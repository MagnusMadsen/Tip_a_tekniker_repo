#!/usr/bin/env python3
import sys
import time
from pymodbus.client import ModbusTcpClient

IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 502

UNITS = [1, 0, 255]
SCAN_START = 0
SCAN_END = 300          # scan 0..299
STEP_DELAY = 0.02       # small delay to avoid flooding
TIMEOUT = 2

def ok(resp) -> bool:
    return resp is not None and hasattr(resp, "isError") and (not resp.isError())

def scan_func(client, unit: int, label: str, fn, start: int, end: int, count: int = 1):
    """
    Scans for first valid address for a given Modbus function.
    """
    print(f"\n[*] Scanning {label} (unit={unit}) addresses {start}..{end-1}")
    first = None
    for addr in range(start, end):
        try:
            rr = fn(address=addr, count=count, device_id=unit)
        except Exception as e:
            print(f"[!] {label} addr={addr} exception: {e}")
            return None

        if ok(rr):
            val = getattr(rr, "bits", None)
            if val is None:
                val = getattr(rr, "registers", None)
            print(f"[+] VALID {label}: addr={addr} -> {val}")
            first = addr
            break

        time.sleep(STEP_DELAY)

    if first is None:
        print(f"[-] No valid {label} found in range.")
    return first

def main():
    client = ModbusTcpClient(IP, port=PORT, timeout=TIMEOUT)
    if not client.connect():
        print(f"[!] Could not connect to {IP}:{PORT}")
        return 1

    print(f"[+] Connected to {IP}:{PORT}")

    for unit in UNITS:
        print(f"\n=== Trying unit={unit} ===")

        scan_func(client, unit, "COILS(0x01)", client.read_coils, SCAN_START, SCAN_END, count=8)
        scan_func(client, unit, "DISCRETE_INPUTS(0x02)", client.read_discrete_inputs, SCAN_START, SCAN_END, count=8)
        scan_func(client, unit, "HOLDING_REGS(0x03)", client.read_holding_registers, SCAN_START, SCAN_END, count=4)
        scan_func(client, unit, "INPUT_REGS(0x04)", client.read_input_registers, SCAN_START, SCAN_END, count=4)

    client.close()
    print("\n[+] Done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
