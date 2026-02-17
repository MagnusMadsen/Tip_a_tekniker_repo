#!/usr/bin/env python3

from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock

#Slave 
LISTEN_IP = "172.16.4.50"
LISTEN_PORT = 502

UNIT_ID = 1
REG_COUNT = 100

# Sæt evt. nogle startværdier
TARGET_REG = 2
TARGET_VALUE = 43

#Master
LISTEN_IP = "172.16.4.51"
LISTEN_PORT = 502
UNIT_ID = 1
REG_COUNT = 100



def main():
    hr_block = ModbusSequentialDataBlock(0, [0] * REG_COUNT)
    hr_block.setValues(TARGET_REG, [TARGET_VALUE])

    store = ModbusSlaveContext(hr=hr_block)
    context = ModbusServerContext(slaves={UNIT_ID: store}, single=False)

    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))


    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*REG_COUNT),
        co=ModbusSequentialDataBlock(0, [0]*REG_COUNT),
        hr=ModbusSequentialDataBlock(0, [0]*REG_COUNT),
        ir=ModbusSequentialDataBlock(0, [0]*REG_COUNT),
    )

    context = ModbusServerContext(slaves={UNIT_ID: store}, single=False)

    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

if __name__ == "__main__":
    main()


