#!/usr/bin/env python3
import asyncio
import struct

# Konfig
LISTEN_IP = "172.16.4.50"  # eth1 IP som windows2 ser
FORWARD_IP = "172.16.4.50"  # eth0 IP (windows1)
FORWARD_PORT = 502

async def forward_to_real_master(reader, writer):
    """Forward request fra slave til rigtig master og returnér svar"""
    try:
        # Læs fuld Modbus request
        header = await reader.readexactly(7)
        tid, pid, len_bytes, uid, func = struct.unpack('>HHHB B', header)
        pdu_len = len_bytes - 1
        pdu = b''
        if pdu_len > 0:
            pdu = await reader.readexactly(pdu_len)
        
        # Send til real master
        master_reader, master_writer = await asyncio.open_connection(FORWARD_IP, FORWARD_PORT)
        await master_writer.write(header + pdu)
        await master_writer.drain()
        
        # Læs svar fra master
        master_header = await master_reader.readexactly(7)
        master_tid, master_pid, master_len_bytes, master_uid, master_func = struct.unpack('>HHHB B', master_header)
        master_pdu_len = master_len_bytes - 1
        master_pdu = b''
        if master_pdu_len > 0:
            master_pdu = await master_reader.readexactly(master_pdu_len)
        
        master_writer.close()
        await master_writer.wait_closed()
        
        # Send svar tilbage til slave
        response_header = struct.pack('>HHHB B', master_tid, master_pid, master_len_bytes, master_uid, master_func)
        writer.write(response_header + master_pdu)
        await writer.drain()
        
    except Exception as e:
        print(f"Forward fejl: {e}")
        exc_header = struct.pack('>HHHBB', tid, pid, 3, uid, 0x01)
        writer.write(exc_header)
        await writer.drain()

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Ny forbindelse fra {addr}")
    
    while True:
        try:
            await forward_to_real_master(reader, writer)
        except:
            break
    
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, LISTEN_IP, 502)
    print(f"Modbus Master Proxy lytter på {LISTEN_IP}:502 -> forwarder til {FORWARD_IP}:502")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())