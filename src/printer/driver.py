from __future__ import annotations

import asyncio
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Protocol

import structlog

from src.config import Settings, get_settings

log = structlog.get_logger()


def _write_latest(output_dir: Path, png_bytes: bytes) -> Path:
    """Write a timestamped PNG and refresh the output/latest.png symlink."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"{stamp}.png"
    path.write_bytes(png_bytes)

    latest = output_dir / "latest.png"
    if latest.is_symlink() or latest.exists():
        try:
            latest.unlink()
        except OSError:
            pass
    try:
        os.symlink(path.name, latest)
    except OSError:
        latest.write_bytes(png_bytes)
    return path


class Driver(Protocol):
    async def print(self, png_bytes: bytes, feed_lines: int | None = None) -> Path: ...


class MockDriver:
    """Saves the PNG to disk and updates output/latest.png. No BLE."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def print(self, png_bytes: bytes, feed_lines: int | None = None) -> Path:
        path = _write_latest(self.output_dir, png_bytes)
        log.info("mock_print", path=str(path), bytes=len(png_bytes))
        return path


class BlePrinterDriver:
    """Sends a PNG to the printer over BLE using the 51 78 protocol that
    demonstrably printed the calibration page. Writes chunked command bytes to
    the ae01 characteristic with a small inter-chunk delay (no notification
    handshake — this firmware doesn't send completion notifications).

    Also saves a copy of the PNG to output/ so /preview/latest works.
    """

    WRITE_CHAR = "0000ae01-0000-1000-8000-00805f9b34fb"
    CHUNK_SIZE = 180
    # Pace the send to the head's physical print speed. Blasting all data at
    # once overruns the printer's line buffer on long jobs -> rows desync and
    # overlap near the end. ~12ms per printed row keeps the buffer from
    # overflowing. (One 48-byte row ~= 56 bytes on the wire incl. framing.)
    ROW_TIME_S = 0.012
    DRAIN_PER_ROW_S = 0.010   # extra wait at the end so the buffer fully prints

    def __init__(
        self,
        mac: str,
        output_dir: Path | None = None,
        energy: int | None = None,
    ) -> None:
        self.mac = mac
        self.output_dir = output_dir
        self.energy = energy

    async def print(self, png_bytes: bytes, feed_lines: int | None = None) -> Path:
        from PIL import Image

        from src.printer import protocol as p

        img = Image.open(io.BytesIO(png_bytes))
        energy = self.energy if self.energy is not None else p.DEFAULT_ENERGY
        feed = p.DEFAULT_FEED_LINES if feed_lines is None else feed_lines

        # Control commands match the captured app exactly (SET_QUALITY 0x33,
        # SET_ENERGY 0x6b12, APPLY 00 01). Feed is per-call so consecutive
        # blocks can sit close together (small feed) and only the final block
        # feeds enough to clear the tear edge.
        payload = p.image_to_commands(img, energy=energy, feed_lines=feed)
        await self._print_one(payload, rows=img.height)
        log.info("ble_print", mac=self.mac, rows=img.height, bytes=len(payload), feed=feed)

        if self.output_dir is not None:
            return _write_latest(self.output_dir, png_bytes)
        return Path("(not saved)")

    async def _resolve_target(self):
        """Return something BleakClient can connect to as a BLE (LE) device.

        On Linux/BlueZ, connecting to a bare MAC string makes BlueZ guess the
        transport and it picks Classic (BR/EDR) -> NotAvailable
        'br-connection-profile-unavailable'. Discovering the device via an LE
        scan first yields a BLEDevice tagged as LE, so the connection uses the
        right transport. Falls back to the raw address (works on macOS).
        """
        from bleak import BleakScanner

        try:
            dev = await BleakScanner.find_device_by_address(self.mac, timeout=12.0)
            if dev is not None:
                return dev
            log.warning("ble_device_not_found_in_scan", mac=self.mac)
        except Exception as e:
            log.warning("ble_scan_failed", error=str(e))
        return self.mac

    async def _print_one(self, payload: bytes, rows: int) -> None:
        from bleak import BleakClient

        n_chunks = max(1, (len(payload) + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE)
        # Spread the per-row print time across the chunks so total send time
        # tracks how long the head takes to physically print the page.
        per_chunk_delay = (rows * self.ROW_TIME_S) / n_chunks

        target = await self._resolve_target()
        # pair=False: this printer has no BR/EDR pairing; BlueZ's default
        # pair-before-connect stalls and times out on Linux. Disabling it makes
        # the LE connect succeed. (No-op on macOS.) Longer timeout for headroom.
        try:
            client = BleakClient(target, timeout=40.0, pair=False)
        except TypeError:
            client = BleakClient(target, timeout=40.0)
        await client.connect()
        try:
            for i in range(0, len(payload), self.CHUNK_SIZE):
                await client.write_gatt_char(
                    self.WRITE_CHAR, payload[i:i + self.CHUNK_SIZE], response=False
                )
                await asyncio.sleep(per_chunk_delay)
            # Stay connected until the buffer has drained (scaled to height).
            await asyncio.sleep(2.0 + rows * self.DRAIN_PER_ROW_S)
        finally:
            await client.disconnect()


def get_driver(settings: Settings | None = None) -> Driver:
    s = settings or get_settings()
    if s.printer_driver == "ble":
        if not s.printer_mac:
            raise RuntimeError("PRINTER_DRIVER=ble but PRINTER_MAC is unset")
        return BlePrinterDriver(s.printer_mac, Path(s.output_dir))
    return MockDriver(Path(s.output_dir))
