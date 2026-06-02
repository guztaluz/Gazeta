#!/usr/bin/env bash
# Start the in-container Bluetooth stack, then the Gazeta service.
# The host provides the kernel BT stack + dongle (hci0); we provide bluetoothd.
set -e

echo "[entrypoint] starting dbus..."
mkdir -p /run/dbus
rm -f /run/dbus/pid
dbus-daemon --system --fork

echo "[entrypoint] starting bluetoothd..."
/usr/libexec/bluetooth/bluetoothd --experimental &
sleep 2

# Bring the adapter up (best-effort; container needs NET_ADMIN + host net).
if command -v hciconfig >/dev/null 2>&1; then
  hciconfig hci0 up 2>/dev/null || echo "[entrypoint] hciconfig hci0 up failed (continuing)"
fi

echo "[entrypoint] launching service on :${SERVICE_PORT:-8080}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${SERVICE_PORT:-8080}"
