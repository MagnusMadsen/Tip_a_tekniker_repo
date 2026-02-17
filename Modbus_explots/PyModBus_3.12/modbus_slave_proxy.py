#!/usr/bin/env python3
import socket
import struct
import logging

logging.basicConfig(filename='slave_eth0.log', level=logging.INFO, format='%(asctime)s %(message)s')

def handle_modbus_request(data):
    """Simpel Modbus slave response"""
    if len(data) < 8:
        return struct.pack('>HHHBB', 0x0001, 0x0000, 0x0003, 0x01, 0x81)  # Error
    
    tid, pid, length, uid, fc = struct.unpack('>HHHBB', data[:7])
    
    if fc == 0x03:  # Read Holding Registers
        addr = struct.unpack('>H', data[7:9])[0]
        count = struct.unpack('>H', data[9:11])[0]
        regs = [42, 100, 200, 300, 500][:count]  # Fake data
        
        pdu = bytes([fc, len(regs)*2]) + b''.join(struct.pack('>H', r) for r in regs)
        resp_len = 3 + len(pdu)
        
    else:
        pdu = bytes([fc + 0x80, 0x01])  # Illegal function
        resp_len = 3 + len(pdu)
    
    return struct.pack('>HHH', tid, pid, resp_len) + bytes([uid]) + pdu

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('172.16.4.51', 502))
sock.listen(5)

print("=== SLAVE på 172.16.4.51:502 startet ===")
print("Master kan connecte nu!")

while True:
    client, addr = sock.accept()
    print(f"Master connected: {addr}")
    
    try:
        data = client.recv(1024)
        if data:
            response = handle_modbus_request(data)
            client.send(response)
            logging.info(f"Req from {addr}: {data.hex()} -> Resp: {response.hex()}")
    except:
        pass
    finally:
        client.close()