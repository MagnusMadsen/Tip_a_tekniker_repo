#!/usr/bin/env python3

import socket
import threading
import time
import sys

# Konfiguration
MASTER_IP = "172.16.4.50"  # eth0
SLAVE_IP = "172.16.4.51"   # eth1
PORT = 502

def forward_traffic(source_sock, dest_sock, direction):
    """Forward data bi-directionelt"""
    try:
        while True:
            data = source_sock.recv(4096)
            if not data:
                break
            dest_sock.send(data)
            sys.stdout.write(f"[{direction}] {len(data)} bytes\n")
            sys.stdout.flush()
    except:
        pass
    finally:
        source_sock.close()
        dest_sock.close()

def handle_master_connection(client_sock, client_addr):
    """Håndter master -> slave forbindelse"""
    print(f"[+] Master {client_addr} connected")
    try:
        slave_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        slave_sock.connect((SLAVE_IP, PORT))
        print(f"[+] Connected to slave {SLAVE_IP}:{PORT}")
        
        # Start forwarding threads
        to_slave = threading.Thread(target=forward_traffic, args=(client_sock, slave_sock, "M->S"))
        to_master = threading.Thread(target=forward_traffic, args=(slave_sock, client_sock, "S->M"))
        
        to_slave.start()
        to_master.start()
        
        to_slave.join()
        to_master.join()
        
    except Exception as e:
        print(f"[!] Master proxy error: {e}")
    finally:
        client_sock.close()

def handle_slave_connection(client_sock, client_addr):
    """Håndter slave -> master forbindelse"""  
    print(f"[+] Slave {client_addr} connected")
    try:
        master_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        master_sock.connect((MASTER_IP, PORT))
        print(f"[+] Connected to master {MASTER_IP}:{PORT}")
        
        # Start forwarding threads
        to_master = threading.Thread(target=forward_traffic, args=(client_sock, master_sock, "S->M"))
        to_slave = threading.Thread(target=forward_traffic, args=(master_sock, client_sock, "M->S"))
        
        to_master.start()
        to_slave.start()
        
        to_master.join()
        to_slave.join()
        
    except Exception as e:
        print(f"[!] Slave proxy error: {e}")
    finally:
        client_sock.close()

def master_proxy():
    """Lyt for master på eth0"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((MASTER_IP, PORT))
    server.listen(20)
    print(f"[+] Master proxy listening: {MASTER_IP}:{PORT}")
    
    while True:
        try:
            client_sock, addr = server.accept()
            t = threading.Thread(target=handle_master_connection, args=(client_sock, addr))
            t.daemon = True
            t.start()
        except Exception as e:
            print(f"[!] Master accept error: {e}")

def slave_proxy():
    """Lyt for slave på eth1"""  
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SLAVE_IP, PORT))
    server.listen(20)
    print(f"[+] Slave proxy listening: {SLAVE_IP}:{PORT}")
    
    while True:
        try:
            client_sock, addr = server.accept()
            t = threading.Thread(target=handle_slave_connection, args=(client_sock, addr))
            t.daemon = True
            t.start()
        except Exception as e:
            print(f"[!] Slave accept error: {e}")

if __name__ == "__main__":
    print("=== SIMPLE Modbus MITM Proxy ===")
    print(f"Master: {MASTER_IP}:{PORT} <-eth0-> {SLAVE_IP}:{PORT}")
    print(f"Slave:  {SLAVE_IP}:{PORT} <-eth1-> {MASTER_IP}:{PORT}")
    print("Pure transparent proxy - ingen manipulation!")
    
    # Start threads
    mt = threading.Thread(target=master_proxy)
    st = threading.Thread(target=slave_proxy)
    
    mt.daemon = True
    st.daemon = True
    mt.start()
    st.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopped")