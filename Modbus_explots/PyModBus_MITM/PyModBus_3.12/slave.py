#!/usr/bin/env python3
import logging

from pymodbus.datastore import ModbusSparseDataBlock, ModbusServerContext
from pymodbus.datastore.context import ModbusDeviceContext
from pymodbus.server.startstop import StartTcpServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_context() -> ModbusServerContext:
    # Enkle datablocks med lidt demo-data:
    di = ModbusSparseDataBlock({0: 0})
    co = ModbusSparseDataBlock({0: 0})
    hr = ModbusSparseDataBlock({0: 0, 1: 456})  # Holding registers
    ir = ModbusSparseDataBlock({0: 111, 1: 222})  # Input registers

    device = ModbusDeviceContext(di=di, co=co, hr=hr, ir=ir)

    # Unit-id 1 (klassisk)
    return ModbusServerContext(devices={1: device}, single=False)


if __name__ == "__main__":
    context = build_context()

    # Hvis du vil binde til en specifik IP i namespace'et, så skift "0.0.0.0" til den IP
    StartTcpServer(context=context, address=("0.0.0.0", 502))
