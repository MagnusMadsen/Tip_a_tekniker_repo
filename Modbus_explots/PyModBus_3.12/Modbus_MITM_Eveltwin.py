#!/usr/bin/env python3
from pymodbus.server import StartTcpServer

# ---- datastore compat (pymodbus 2/3/4) ----
try:
    # Newer pymodbus
    from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext, ModbusSparseDataBlock
    NEW_API = True
except Exception:
    # Older pymodbus
    from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
    NEW_API = False

LISTEN_IP = "0.0.0.0"   # lyt på eth1 også (nemmest)
LISTEN_PORT = 502
UNIT_ID = 1

REG_COUNT = 100

def main():
    # SparseDataBlock: map register->værdi
    hr = ModbusSparseDataBlock({i: 0 for i in range(REG_COUNT)})

    if NEW_API:
        device = ModbusDeviceContext(hr=hr)
        context = ModbusServerContext(devices=device, single=True)
    else:
        slave = ModbusSlaveContext(hr=hr)
        context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

if __name__ == "__main__":
    main()
