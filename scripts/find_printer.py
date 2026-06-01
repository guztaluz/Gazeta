"""Scan for the BLE thermal printer and print its address + GATT layout.

Run with the printer powered on and NOT connected to the Tiny Print phone app
(BLE peripherals usually allow only one connection at a time).

    .venv/bin/python scripts/find_printer.py

On macOS the "address" is a CoreBluetooth UUID, not a real MAC — that's normal.
It'll be a real MAC when we scan from the Linux NAS later. Copy whichever
identifier this prints into PRINTER_MAC in .env.

To inspect a specific device's GATT services directly:
    .venv/bin/python scripts/find_printer.py <ADDRESS>
"""
from __future__ import annotations

import asyncio
import sys

from bleak import BleakClient, BleakScanner

# Cheap 57mm thermal printers show up under many names.
NAME_HINTS = (
    "print", "mx", "x6", "gb0", "gt0", "yhk", "cat", "mini",
    "thermal", "peripage", "ph", "gb0", "_a", "bq0",
)


async def dump_services(address: str) -> None:
    try:
        async with BleakClient(address) as client:
            for svc in client.services:
                print(f"  service {svc.uuid}")
                for ch in svc.characteristics:
                    props = ",".join(ch.properties)
                    print(f"    char  {ch.uuid}  [{props}]")
    except Exception as e:
        print(f"  could not connect: {e}")


async def scan() -> None:
    print("Scanning for BLE devices (8s)...\n")
    devices = await BleakScanner.discover(timeout=8.0, return_adv=True)

    if not devices:
        print("No BLE devices found. Is Bluetooth on? Did macOS grant the terminal BT permission?")
        return

    rows = []
    for addr, (dev, adv) in devices.items():
        name = (dev.name or adv.local_name or "").strip()
        rows.append((adv.rssi, addr, name))
    rows.sort(reverse=True)  # strongest signal first

    print(f"{'RSSI':>5}  {'ADDRESS':38}  NAME")
    print("-" * 70)
    candidates = []
    for rssi, addr, name in rows:
        flag = ""
        if name and any(h in name.lower() for h in NAME_HINTS):
            flag = "  <-- likely printer"
            candidates.append((addr, name))
        print(f"{rssi:>5}  {addr:38}  {name or '(no name)'}{flag}")

    if not candidates:
        print("\nNo obvious printer by name. If you know which row it is, re-run with its address:")
        print("    .venv/bin/python scripts/find_printer.py <ADDRESS>")
        return

    for addr, name in candidates:
        print(f"\n=== GATT layout for {name} ({addr}) ===")
        await dump_services(addr)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(dump_services(sys.argv[1]))
    else:
        asyncio.run(scan())
