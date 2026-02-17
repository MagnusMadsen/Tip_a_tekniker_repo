#!/usr/bin/env python3
from pymodbus.server import StartTcpServer
from pymodbus.client import ModbusTcpClient

from pymodbus.datastore.store import ModbusSequentialDataBlock
from pymodbus.datastore.context import ModbusSlaveContext, ModbusServerContext

LISTEN_IP = "172.16.4.51"
LISTEN_PORT = 502
UNIT_ID = 1

UPSTREAM_IP = "172.16.4.50"
UPSTREAM_PORT = 502
UPSTREAM_UNIT = 1

class ProxyHoldingBlock(ModbusSequentialDataBlock):
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
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*100),
        co=ModbusSequentialDataBlock(0, [0]*100),
        hr=ProxyHoldingBlock(0, [0]*100),
        ir=ModbusSequentialDataBlock(0, [0]*100),
    )
    context = ModbusServerContext(slaves={UNIT_ID: store}, single=False)
    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

if __name__ == "__main__":
    main()
