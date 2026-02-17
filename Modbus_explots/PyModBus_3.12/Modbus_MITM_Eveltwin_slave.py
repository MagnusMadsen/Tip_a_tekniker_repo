#!/usr/bin/env python3
import asyncio
import socket
from pymodbus.server.async_io import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import struct

# Konfig
LISTEN_IP = "172.16.4.51"  # eth0 IP som Windows1 ser
FORWARD_IP = "172.16.4.51"  # eth1 IP (windows2)
FORWARD_PORT = 502

# Minimal datastore (bare for at holde forbindelse alive)
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0]*100),
    co=ModbusSequentialDataBlock(0, [0]*100),
    hr=ModbusSequentialDataBlock(0, [0]*100),
    ir=ModbusSequentialDataBlock(0, [0]*100))
context = ModbusServerContext(slaves=store, single=True)

async def forward_to_real_slave(reader, writer):
    """Forward request til rigtig slave og returnér svar"""
    try:
        # Læs Modbus TCP header (7 bytes) + PDU
        header = await reader.readexactly(7)
        tid, pid, len_bytes, uid, func = struct.unpack('>HHHB B', header)
        pdu_len = len_bytes - 1
        
        pdu = b''
        if pdu_len > 0:
            pdu = await reader.readexactly(pdu_len)
        
        # Send til real slave
        slave_reader, slave_writer = await asyncio.open_connection(FORWARD_IP, FORWARD_PORT)
        await slave_writer.write(header + pdu)
        await slave_writer.drain()
        
        # Læs svar
        slave_header = await slave_reader.readexactly(7)
        slave_tid, slave_pid, slave_len_bytes, slave_uid, slave_func = struct.unpack('>HHHB B', slave_header)
        slave_pdu_len = slave_len_bytes - 1
        slave_pdu = b''
        if slave_pdu_len > 0:
            slave_pdu = await slave_reader.readexactly(slave_pdu_len)
        
        slave_writer.close()
        await slave_writer.wait_closed()
        
        # Send svar tilbage
        response_header = struct.pack('>HHHB B', slave_tid, slave_pid, slave_len_bytes, slave_uid, slave_func)
        writer.write(response_header + slave_pdu)
        await writer.drain()
        
    except Exception as e:
        print(f"Forward fejl: {e}")
        # Send exception response
        exc_header = struct.pack('>HHHBB', tid, pid, 3, uid, 0x01)  # Illegal function
        writer.write(exc_header)
        await writer.drain()

async def handle_client(reader, writer):
    """Håndter hver klient-forbindelse"""
    addr = writer.get_extra_info('peername')
    print(f"Ny forbindelse fra {addr}")
    
    while True:
        try:
            await forward_to_real_slave(reader, writer)
        except asyncio.IncompleteReadError:
            break
        except Exception as e:
            print(f"Client håndtering fejl: {e}")
            break
    
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, LISTEN_IP, 502)
    print(f"Modbus Slave Proxy lytter på {LISTEN_IP}:502 -> forwarder til {FORWARD_IP}:502")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())