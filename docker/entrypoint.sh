#!/usr/bin/env bash
# Start the in-container Bluetooth stack, then the Gazeta service.
# The host provides the kernel BT stack + dongle (hci0); we provide bluetoothd.
#
# IMPORTANT: Bluetooth setup must NEVER block or kill the service. Each BT step
# is best-effort and backgrounded/guarded; uvicorn always starts.

echo "[entrypoint] starting dbus..."
mkdir -p /run/dbus
rm -f /run/dbus/pid
dbus-daemon --system --fork || echo "[entrypoint] dbus-daemon failed (continuing)"

# Force BlueZ into LE-only mode (the X6h is BLE-only; BR/EDR attempts fail
# with 'br-connection-profile-unavailable').
mkdir -p /etc/bluetooth
cat > /etc/bluetooth/main.conf <<'CONF'
[General]
ControllerMode = le
Experimental = true
CONF

echo "[entrypoint] starting bluetoothd (LE-only)..."
/usr/libexec/bluetooth/bluetoothd --experimental >/var/log/bluetoothd.log 2>&1 &
sleep 3

# Best-effort adapter config in a backgrounded subshell so nothing here can
# block or abort the container startup.
(
  hciconfig hci0 up 2>/dev/null || true
  if command -v btmgmt >/dev/null 2>&1; then
    btmgmt power off 2>/dev/null || true
    btmgmt bredr off 2>/dev/null || true
    btmgmt le on    2>/dev/null || true
    btmgmt power on  2>/dev/null || true
  fi
) &

echo "[entrypoint] launching service on :${SERVICE_PORT:-8080}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${SERVICE_PORT:-8080}"
