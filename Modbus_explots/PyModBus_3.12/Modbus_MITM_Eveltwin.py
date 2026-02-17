#!/usr/bin/env python3
import logging
from datetime import datetime

from pymodbus.server import StartTcpServer

# Datastore-API varierer mellem pymodbus versioner, så vi holder det kompatibelt
try:
    # Nyere pymodbus
    from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext, ModbusSparseDataBlock
    NEW_API = True
except Exception:
    # Ældre pymodbus
    from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
    NEW_API = False

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 502
UNIT_ID = 1
REG_COUNT = 100

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class VerboseHR(ModbusSparseDataBlock):
    def getValues(self, address, count=1):
        values = super().getValues(address, count)
        print(f"[{ts()}] HR READ  addr={address} count={count} -> {values}")
        return values

    def setValues(self, address, values):
        print(f"[{ts()}] HR WRITE addr={address} values={list(values)}")
        return super().setValues(address, values)

def main():
    # Mest mulig pymodbus-log i terminalen
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    hr = VerboseHR({i: 0 for i in range(REG_COUNT)})

    if NEW_API:
        device = ModbusDeviceContext(hr=hr)
        context = ModbusServerContext(devices=device, single=True)
    else:
        slave = ModbusSlaveContext(hr=hr)
        context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    print(f"[{ts()}] Starting Modbus TCP SLAVE on {LISTEN_IP}:{LISTEN_PORT} unit={UNIT_ID}")
    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

if __name__ == "__main__":
    main()
