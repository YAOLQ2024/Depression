"""
ble_receiver.py
---------------
BLE NUS 接收器，与 EEGSerialReceiver 同接口，
用于 Windows 采集端通过 BLE 接收脑电帽数据，再桥接到 LSL。

依赖: pip install bleak
"""

import asyncio
import struct
import threading
import time
from typing import Callable, Optional

from eeg_serial import (
    FEAT_TOTAL,
    NUM_CH,
    PKT_TYPE_FEAT,
    PKT_TYPE_WAVE,
    WAVE_TOTAL,
    FeaturePacket,
    WavePacket,
    _parse_feat_payload,
    crc16_ccitt,
)

NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

SYNC_0 = 0x06
SYNC_1 = 0x09


class BLEEEGReceiver:
    """
    BLE 版 EEG 接收器，接口与 EEGSerialReceiver 一致：
      .start()  .stop()  on_wave / on_feat 回调
    """

    def __init__(
        self,
        address: str,
        on_wave: Optional[Callable[[WavePacket], None]] = None,
        on_feat: Optional[Callable[[FeaturePacket], None]] = None,
    ):
        self.address = address
        self.on_wave = on_wave
        self.on_feat = on_feat

        self._running = False
        self._thread = None
        self._buf = bytearray()

        self.wave_count = 0
        self.feat_count = 0
        self.crc_errors = 0

        self.on_status: Optional[Callable[[str], None]] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._entry, daemon=True, name="BLE-RX")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _log(self, message: str):
        if self.on_status:
            self.on_status(message)
        else:
            print(message)

    def _entry(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        except Exception as exc:
            self._log(f"[BLE] 错误: {exc}")
        finally:
            loop.close()

    async def _run(self):
        from bleak import BleakClient

        self._log(f"[BLE] 连接 {self.address} ...")

        try:
            async with BleakClient(self.address, timeout=15.0) as client:
                self._log(f"[BLE] 已连接  MTU={client.mtu_size}")

                await client.start_notify(NUS_TX_CHAR_UUID, self._on_notify)

                while self._running and client.is_connected:
                    await asyncio.sleep(0.1)

                await client.stop_notify(NUS_TX_CHAR_UUID)

        except Exception as exc:
            self._log(f"[BLE] 连接失败: {exc}")

        self._log("[BLE] 已断开")

    def _on_notify(self, sender, data: bytearray):
        del sender
        self._buf.extend(data)
        self._parse()

    def _parse(self):
        buf = self._buf

        while len(buf) >= 3:
            found = -1
            for i in range(len(buf) - 1):
                if buf[i] == SYNC_0 and buf[i + 1] == SYNC_1:
                    found = i
                    break
            if found < 0:
                buf = buf[-1:]
                break
            if found > 0:
                buf = buf[found:]

            if len(buf) < 3:
                break

            ptype = buf[2]
            if ptype == PKT_TYPE_WAVE:
                pkt_len = WAVE_TOTAL
            elif ptype == PKT_TYPE_FEAT:
                pkt_len = FEAT_TOTAL
            else:
                buf = buf[1:]
                continue

            if len(buf) < pkt_len:
                break

            frame = bytes(buf[:pkt_len])
            buf = buf[pkt_len:]

            crc_calc = crc16_ccitt(frame[:-2])
            crc_recv = (frame[-2] << 8) | frame[-1]
            if crc_calc != crc_recv:
                self.crc_errors += 1
                continue

            if ptype == PKT_TYPE_WAVE:
                seq = struct.unpack("<H", frame[3:5])[0]
                channels = list(struct.unpack("<3f", frame[5:17]))
                if self.on_wave:
                    self.on_wave(WavePacket(seq=seq, ch=channels))
                self.wave_count += 1

            elif ptype == PKT_TYPE_FEAT:
                feature_packet = _parse_feat_payload(frame[3:75])
                if feature_packet and self.on_feat:
                    self.on_feat(feature_packet)
                    self.feat_count += 1

        self._buf = bytearray(buf)


def scan_and_select(timeout: float = 5.0) -> Optional[str]:
    """扫描 BLE 设备，让用户选择，返回地址。"""
    from bleak import BleakScanner

    print(f"[BLE] 正在扫描 ({timeout}s) ...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    devices = loop.run_until_complete(BleakScanner.discover(timeout=timeout))
    loop.close()

    if not devices:
        print("[BLE] 未发现任何设备")
        return None

    dev_list = []
    for device in devices:
        name = device.name or "未知"
        rssi = device.rssi if hasattr(device, "rssi") else -999
        is_eeg = "EEG" in name.upper()
        dev_list.append((is_eeg, rssi, name, device.address))

    dev_list.sort(key=lambda item: (-item[0], -item[1]))

    print(f"\n  发现 {len(dev_list)} 个设备:")
    print(f'  {"#":>3}  {"名称":<20} {"地址":<20} {"RSSI":>6}')
    print(f'  {"─" * 3}  {"─" * 20} {"─" * 20} {"─" * 6}')

    for index, (is_eeg, rssi, name, addr) in enumerate(dev_list):
        marker = " ★" if is_eeg else ""
        print(f"  {index + 1:3d}  {name:<20} {addr:<20} {rssi:>4} dBm{marker}")

    print()
    selection = input("  输入编号连接 (或直接输入MAC地址, q退出): ").strip()

    if selection.lower() == "q":
        return None

    if ":" in selection or "-" in selection:
        return selection

    try:
        idx = int(selection) - 1
        if 0 <= idx < len(dev_list):
            return dev_list[idx][3]
    except ValueError:
        pass

    print("[BLE] 无效选择")
    return None


if __name__ == "__main__":
    address = scan_and_select()
    if not address:
        raise SystemExit(0)

    def on_feat(packet):
        print(
            f"[FEAT] FAA={packet.FAA:+.4f}  "
            f"HFD=[{packet.HFD[0]:.3f},{packet.HFD[1]:.3f},{packet.HFD[2]:.3f}]"
        )

    def on_wave(packet):
        del packet

    receiver = BLEEEGReceiver(address, on_wave=on_wave, on_feat=on_feat)
    receiver.start()

    try:
        while True:
            time.sleep(5)
            print(
                f"  wave={receiver.wave_count}  feat={receiver.feat_count}  "
                f"crc_err={receiver.crc_errors}"
            )
    except KeyboardInterrupt:
        receiver.stop()
