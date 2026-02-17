#!/usr/bin/env python3
import time
from datetime import datetime
from pymodbus.client import ModbusTcpClient

# ---- Windows slave (den fysiske) ----
WIN_SLAVE_IP = "172.16.4.51"   # RET til Windows-slavens IP (IKKE din Kali IP)
WIN_SLAVE_PORT = 502
UNIT_ID = 1

# ---- hvad vil du skrive ----
TARGET_REG = 2
VALUE = 999
INTERVAL_SEC = 1

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    c = ModbusTcpClient(WIN_SLAVE_IP, port=WIN_SLAVE_PORT)

    while True:
        if not c.connect():
            print(f"[{ts()}] connect FAILED -> {WIN_SLAVE_IP}:{WIN_SLAVE_PORT}")
            time.sleep(1)
            continue

        # pymodbus 3.x+: bruger "unit=" (ikke "slave=")
        wr = c.write_register(TARGET_REG, VALUE, unit=UNIT_ID)

        if wr and not wr.isError():
            print(f"[{ts()}] wrote {VALUE} to HR[{TARGET_REG}] on {WIN_SLAVE_IP} unit={UNIT_ID}")
        else:
            print(f"[{ts()}] write FAILED: {wr}")

        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()
