#!/usr/bin/env python3
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 502

class LogBlock(ModbusSequentialDataBlock):
    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        print(f"[READ]  addr={address} count={count} -> {vals}")
        return vals

    def setValues(self, address, values):
        print(f"[WRITE] addr={address} values={values}")
        super().setValues(address, values)

block = LogBlock(0, [0] * 100)
block.setValues(2, [500])  # HR[2]=500

store = ModbusSlaveContext(hr=block)  # kun holding registers
context = ModbusServerContext(slaves=store, single=True)

print(f"[+] Modbus slave listening on {LISTEN_IP}:{LISTEN_PORT}")
StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

