#!/usr/bin/env python3
from pymodbus.server import StartTcpServer
from pymodbus.client import ModbusTcpClient

# ---- compat imports (pymodbus 2.x / 3.x / 4.x-ish) ----
try:
    # Newer: DeviceContext style
    from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext
except Exception:
    ModbusDeviceContext = None
    from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext  # older

try:
    from pymodbus.datastore import ModbusSequentialDataBlock as DataBlock
except Exception:
    # Newer builds often have Sparse datablock instead
    from pymodbus.datastore import ModbusSparseDataBlock as DataBlock

# Fake slave (din maskine)
LISTEN_IP = "172.16.4.51"
LISTEN_PORT = 502
UNIT_ID = 1

# Upstream (den du forwarder til)
UPSTREAM_IP = "172.16.4.50"
UPSTREAM_PORT = 502
UPSTREAM_UNIT = 1

REG_COUNT = 100

class ProxyHoldingBlock(DataBlock):
    def __init__(self):
        # Sequential: (0, [0]*N)  |  Sparse: ([0]*N) virker i nyere docs
        try:
            super().__init__(0, [0] * REG_COUNT)
        except TypeError:
            super().__init__([0] * REG_COUNT)

    def getValues(self, address, count=1):
        c = ModbusTcpClient(UPSTREAM_IP, port=UPSTREAM_PORT)
        if not c.connect():
            return super().getValues(address, count)
        try:
            rr = c.read_holding_registers(address, count, slave=UPSTREAM_UNIT)
            if rr and not rr.isError():
                return rr.registers
            return super().getValues(address, count)
        finally:
            c.close()

    def setValues(self, address, values):
        c = ModbusTcpClient(UPSTREAM_IP, port=UPSTREAM_PORT)
        if not c.connect():
            return super().setValues(address, values)
        try:
            if len(values) == 1:
                wr = c.write_register(address, values[0], slave=UPSTREAM_UNIT)
            else:
                wr = c.write_registers(address, values, slave=UPSTREAM_UNIT)
            if wr and not wr.isError():
                return
            return super().setValues(address, values)
        finally:
            c.close()

def main():
    # Lav datablocks
    di = DataBlock([0] * REG_COUNT) if DataBlock.__name__ == "ModbusSparseDataBlock" else DataBlock(0, [0] * REG_COUNT)
    co = DataBlock([0] * REG_COUNT) if DataBlock.__name__ == "ModbusSparseDataBlock" else DataBlock(0, [0] * REG_COUNT)
    ir = DataBlock([0] * REG_COUNT) if DataBlock.__name__ == "ModbusSparseDataBlock" else DataBlock(0, [0] * REG_COUNT)
    hr = ProxyHoldingBlock()

    # Nyere API: ModbusDeviceContext / ældre: ModbusSlaveContext
    if ModbusDeviceContext:
        device = ModbusDeviceContext(di=di, co=co, hr=hr, ir=ir)
        context = ModbusServerContext(devices=device, single=True)
    else:
        slave = ModbusSlaveContext(di=di, co=co, hr=hr, ir=ir)
        context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

if __name__ == "__main__":
    main()
