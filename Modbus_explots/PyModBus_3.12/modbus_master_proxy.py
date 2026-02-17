#!/usr/bin/env python3
import socket
import struct
import time
import logging

logging.basicConfig(filename='master_eth1.log', level=logging.INFO, format='%(asctime)s %(message)s')

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('172.16.4.50', 502))
sock.listen(5)

print("=== MASTER på 172.16.4.50:502 startet ===")
print("Slave kan connecte nu!")

while True:
    client, addr = sock.accept()
    print(f"Slave connected: {addr}")
    
    data = client.recv(1024)
    if data:
        tid = struct.unpack('>H', data[0:2])[0]
        uid = data[6]
        
        # Simuler Read Holding Registers request (fc=03)
        req = struct.pack('>HHHBBHH', tid, 0, 0x0006, uid, 0x03, 0x0000, 0x0004)
        client.send(req)
        logging.info(f"Sent poll to {addr}")
        
        try:
            resp = client.recv(1024)
            print(f"Fra slave {addr}: {resp.hex()}")
            logging.info(f"Resp from {addr}: {resp.hex()}")
        except:
            pass
    
    client.close()