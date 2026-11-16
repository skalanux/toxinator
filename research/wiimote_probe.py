#!/usr/bin/env python3
"""Probe Nintendo Wii Remote evdev nodes exposed by the Linux hid-wiimote driver.

Usage:
    python research/wiimote_probe.py list
    python research/wiimote_probe.py dump --seconds 10
    python research/wiimote_probe.py rumble --ms 200

Requires python-evdev (pip install evdev). No root is needed if the user can
read /dev/input/event* (logind uaccess usually grants it for joystick-class
devices; otherwise add the user to the "input" group).
"""

from __future__ import annotations

import argparse
import glob
import os
import select
import sys
import time

try:
    import evdev
    from evdev import ecodes
except ImportError:  # pragma: no cover - friendlier message
    sys.exit("python-evdev is required: pip install evdev")

PREFIX = "Nintendo Wii Remote"
IR_EMPTY = (1023, 1023)  # empty slot: all 10 bits set (y exceeds nominal max 767)

KEYS = {
    ecodes.BTN_A: "a",
    ecodes.BTN_B: "b",
    ecodes.BTN_1: "1",
    ecodes.BTN_2: "2",
    ecodes.BTN_MODE: "home",
    ecodes.KEY_NEXT: "plus",
    ecodes.KEY_PREVIOUS: "minus",
    ecodes.KEY_UP: "up",
    ecodes.KEY_DOWN: "down",
    ecodes.KEY_LEFT: "left",
    ecodes.KEY_RIGHT: "right",
}


def hid_uevent(event_path: str) -> dict[str, str]:
    """Return the HID parent uevent for an /dev/input/eventN path.

    hid-wiimote does not set input_dev.uniq, so evdev's uniq is empty. The MAC
    lives in the HID parent's uevent (HID_UNIQ) for both HIDP and UHID.
    """
    name = os.path.basename(event_path)
    path = f"/sys/class/input/{name}/device/device/uevent"
    try:
        with open(path, encoding="ascii") as fh:
            return dict(
                line.rstrip("\n").split("=", 1)
                for line in fh
                if "=" in line
            )
    except OSError:
        return {}


def hid_dir_for_mac(mac: str) -> str | None:
    for hdev in glob.glob("/sys/bus/hid/devices/*"):
        try:
            with open(os.path.join(hdev, "uevent"), encoding="ascii") as fh:
                if f"HID_UNIQ={mac}" in fh.read():
                    return hdev
        except OSError:
            continue
    return None


def read_sysfs(path: str) -> str | None:
    try:
        with open(path, encoding="ascii") as fh:
            return fh.read().strip()
    except OSError:
        return None


def open_wiimotes() -> dict[str, dict[str, evdev.InputDevice]]:
    """Group readable Nintendo Wii Remote event nodes by Wiimote MAC."""
    found: dict[str, dict[str, evdev.InputDevice]] = {}
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        if not dev.name.startswith(PREFIX):
            continue
        mac = hid_uevent(path).get("HID_UNIQ") or "unknown"
        found.setdefault(mac, {})[dev.name] = dev
    return found


def describe(mac: str, nodes: dict[str, evdev.InputDevice]) -> None:
    hdev = hid_dir_for_mac(mac) if mac != "unknown" else None
    print(f"Wiimote {mac}")
    if hdev:
        print(f"  hid:       {hdev}")
        print(f"  devtype:   {read_sysfs(os.path.join(hdev, 'devtype'))}")
        print(f"  extension: {read_sysfs(os.path.join(hdev, 'extension'))}")
    for name, dev in sorted(nodes.items()):
        caps = dev.capabilities(verbose=False)
        print(f"  node:      {name}  ({dev.path})")
        print(f"    keys:    {len(caps.get(ecodes.EV_KEY, []))}")
        print(f"    abs:     {sorted(caps.get(ecodes.EV_ABS, []))}")
        print(f"    ff:      {sorted(caps.get(ecodes.EV_FF, []))}")


def cmd_list(_args: argparse.Namespace) -> int:
    if not evdev.list_devices():
        print(
            "No readable /dev/input/event* devices. Check permissions "
            "(input group or logind uaccess)."
        )
        return 1
    found = open_wiimotes()
    if not found:
        print("No Nintendo Wii Remote evdev nodes found.")
        print("Pair it first (red sync + bluetoothctl) and check dmesg.")
        return 1
    for mac, nodes in sorted(found.items()):
        describe(mac, nodes)
        print()
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    found = open_wiimotes()
    if not found:
        print("No Nintendo Wii Remote evdev nodes found.")
        return 1

    devices: list[tuple[str, str, evdev.InputDevice]] = []
    for mac, nodes in found.items():
        for name, dev in nodes.items():
            devices.append((mac, name, dev))
            print(f"listening: {mac} {name} {dev.path}")

    pressed: dict[str, set[str]] = {mac: set() for mac in found}
    accel: dict[str, tuple[int, int, int]] = {mac: (0, 0, 0) for mac in found}
    gyro: dict[str, tuple[int, int, int] | None] = {mac: None for mac in found}
    dots: dict[str, list[tuple[int, int] | None]] = {
        mac: [None] * 4 for mac in found
    }

    fds = {dev.fd: (mac, name, dev) for mac, name, dev in devices}
    deadline = time.monotonic() + args.seconds

    try:
        while time.monotonic() < deadline:
            try:
                ready, _, _ = select.select(list(fds), [], [], 0.05)
            except OSError:
                print("select failed; a device may have disappeared")
                return 1
            for fd in ready:
                mac, name, dev = fds[fd]
                while True:
                    try:
                        ev = dev.read_one()
                    except OSError:
                        print(f"device gone: {mac} {name}")
                        return 1
                    if ev is None:
                        break
                    _handle(ev, mac, name, pressed, accel, gyro, dots)
    except KeyboardInterrupt:
        pass
    return 0


def _handle(ev, mac, name, pressed, accel, gyro, dots) -> None:
    if ev.type == ecodes.EV_KEY and ev.value in (0, 1):
        label = KEYS.get(ev.code)
        if not label:
            return
        if ev.value:
            pressed[mac].add(label)
        else:
            pressed[mac].discard(label)
        print(f"{mac} buttons: {' '.join(sorted(pressed[mac]))}")
    elif ev.type == ecodes.EV_ABS:
        if name.endswith("Accelerometer"):
            idx = {ecodes.ABS_RX: 0, ecodes.ABS_RY: 1, ecodes.ABS_RZ: 2}.get(ev.code)
            if idx is not None:
                values = list(accel[mac])
                values[idx] = ev.value
                accel[mac] = tuple(values)  # type: ignore[assignment]
                print(f"{mac} accel: {accel[mac]}")
        elif name.endswith("Motion Plus"):
            idx = {ecodes.ABS_RX: 0, ecodes.ABS_RY: 1, ecodes.ABS_RZ: 2}.get(ev.code)
            if idx is not None:
                values = list(gyro[mac] or (0, 0, 0))
                values[idx] = ev.value
                gyro[mac] = tuple(values)  # type: ignore[assignment]
                print(f"{mac} gyro: {gyro[mac]}")
        elif name.endswith(" IR"):
            code = ev.code - ecodes.ABS_HAT0X
            slot, axis = divmod(code, 2)
            if 0 <= slot < 4 and axis in (0, 1):
                dot = list(dots[mac][slot] or (0, 0))
                dot[axis] = ev.value
                dots[mac][slot] = (
                    (dot[0], dot[1]) if tuple(dot) != IR_EMPTY else None
                )
                visible = [d for d in dots[mac] if d is not None]
                print(f"{mac} ir: {visible}")


def cmd_rumble(args: argparse.Namespace) -> int:
    found = open_wiimotes()
    if not found:
        print("No Nintendo Wii Remote evdev nodes found.")
        return 1
    from evdev import ff

    for mac, nodes in found.items():
        dev = nodes.get(PREFIX)
        if dev is None:
            continue
        effect = ff.Effect(
            type=ecodes.FF_RUMBLE,
            id=-1,
            direction=0,
            ff_trigger=ff.Trigger(button=0, interval=0),
            ff_replay=ff.Replay(length=args.ms, delay=0),
            u=ff.EffectType(
                ff_rumble_effect=ff.Rumble(
                    strong_magnitude=0xFFFF, weak_magnitude=0xFFFF
                )
            ),
        )
        try:
            effect_id = dev.upload_effect(effect)
            dev.write(ecodes.EV_FF, effect_id, 1)
            print(f"{mac} rumble {args.ms} ms")
        except OSError as exc:
            print(f"{mac} rumble failed: {exc} (open the event node read-write)")
    # Keep the fds open while the effect plays.
    time.sleep(args.ms / 1000.0)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list Wiimotes and their evdev nodes")
    p_list.set_defaults(func=cmd_list)

    p_dump = sub.add_parser("dump", help="print events for N seconds")
    p_dump.add_argument("--seconds", type=float, default=10.0)
    p_dump.set_defaults(func=cmd_dump)

    p_rumble = sub.add_parser("rumble", help="pulse the rumble motor")
    p_rumble.add_argument("--ms", type=int, default=200)
    p_rumble.set_defaults(func=cmd_rumble)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
