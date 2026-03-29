"""
ble_receiver.py
───────────────
BLE NUS 接收器，与 EEGSerialReceiver 同接口，
用于 depression_knn.py 的采集和实时分类模式。

依赖: pip install bleak
"""

import struct
import asyncio
import threading
import time
from typing import Optional, Callable, List

from eeg_serial import (
    FeaturePacket, WavePacket, _parse_feat_payload,
    crc16_ccitt, NUM_CH,
    PKT_TYPE_WAVE, PKT_TYPE_FEAT,
    WAVE_TOTAL, FEAT_TOTAL,
)

NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

SYNC_0 = 0x06
SYNC_1 = 0x09


class BLEEEGReceiver:
    """
    BLE 版 EEG 接收器，接口与 EEGSerialReceiver 一致：
      .start()  .stop()  on_wave / on_feat 回调
    """

    def __init__(self, address: str,
                 on_wave: Optional[Callable[[WavePacket], None]] = None,
                 on_feat: Optional[Callable[[FeaturePacket], None]] = None):
        self.address  = address
        self.on_wave  = on_wave
        self.on_feat  = on_feat

        self._running   = False
        self._thread    = None
        self._buf       = bytearray()

        # 统计
        self.wave_count = 0
        self.feat_count = 0
        self.crc_errors = 0

        # 状态回调 (可选)
        self.on_status: Optional[Callable[[str], None]] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._entry, daemon=True,
                                        name='BLE-RX')
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _log(self, msg: str):
        if self.on_status:
            self.on_status(msg)
        else:
            print(msg)

    # ---- 线程入口 ----
    def _entry(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        except Exception as e:
            self._log(f'[BLE] 错误: {e}')
        finally:
            loop.close()

    async def _run(self):
        from bleak import BleakClient

        self._log(f'[BLE] 连接 {self.address} ...')

        try:
            async with BleakClient(self.address, timeout=15.0) as client:
                self._log(f'[BLE] 已连接  MTU={client.mtu_size}')

                await client.start_notify(NUS_TX_CHAR_UUID, self._on_notify)

                while self._running and client.is_connected:
                    await asyncio.sleep(0.1)

                await client.stop_notify(NUS_TX_CHAR_UUID)

        except Exception as e:
            self._log(f'[BLE] 连接失败: {e}')

        self._log('[BLE] 已断开')

    # ---- BLE 通知回调 ----
    def _on_notify(self, sender, data: bytearray):
        self._buf.extend(data)
        self._parse()

    # ---- 解析 (与 eeg_serial 格式完全一致) ----
    def _parse(self):
        buf = self._buf

        while len(buf) >= 3:
            # 找帧头 [06][09]
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

            # CRC 校验
            crc_calc = crc16_ccitt(frame[:-2])
            crc_recv = (frame[-2] << 8) | frame[-1]
            if crc_calc != crc_recv:
                self.crc_errors += 1
                continue

            # 分发
            if ptype == PKT_TYPE_WAVE:
                seq = struct.unpack('<H', frame[3:5])[0]
                chs = list(struct.unpack('<3f', frame[5:17]))
                if self.on_wave:
                    self.on_wave(WavePacket(seq=seq, ch=chs))
                self.wave_count += 1

            elif ptype == PKT_TYPE_FEAT:
                fp = _parse_feat_payload(frame[3:75])
                if fp and self.on_feat:
                    self.on_feat(fp)
                    self.feat_count += 1

        self._buf = bytearray(buf)


# ================================================================
#  BLE 扫描辅助
# ================================================================

def scan_and_select(timeout: float = 5.0) -> Optional[str]:
    """
    扫描 BLE 设备，让用户选择，返回地址。
    """
    import asyncio
    from bleak import BleakScanner

    print(f'[BLE] 正在扫描 ({timeout}s) ...')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    devices = loop.run_until_complete(BleakScanner.discover(timeout=timeout))
    loop.close()

    if not devices:
        print('[BLE] 未发现任何设备')
        return None

    # 排序: EEG 设备排前面
    dev_list = []
    for d in devices:
        name = d.name or '未知'
        rssi = d.rssi if hasattr(d, 'rssi') else -999
        is_eeg = 'EEG' in name.upper()
        dev_list.append((is_eeg, rssi, name, d.address))

    dev_list.sort(key=lambda x: (-x[0], -x[1]))

    print(f'\n  发现 {len(dev_list)} 个设备:')
    print(f'  {"#":>3}  {"名称":<20} {"地址":<20} {"RSSI":>6}')
    print(f'  {"─"*3}  {"─"*20} {"─"*20} {"─"*6}')

    for i, (is_eeg, rssi, name, addr) in enumerate(dev_list):
        marker = ' ★' if is_eeg else ''
        print(f'  {i+1:3d}  {name:<20} {addr:<20} {rssi:>4} dBm{marker}')

    print()
    sel = input('  输入编号连接 (或直接输入MAC地址, q退出): ').strip()

    if sel.lower() == 'q':
        return None

    # 判断是编号还是地址
    if ':' in sel or '-' in sel:
        return sel

    try:
        idx = int(sel) - 1
        if 0 <= idx < len(dev_list):
            return dev_list[idx][3]
    except ValueError:
        pass

    print('[BLE] 无效选择')
    return None


# ================================================================
#  快速测试
# ================================================================
if __name__ == '__main__':
    addr = scan_and_select()
    if not addr:
        exit()

    def on_feat(f):
        print(f'[FEAT] FAA={f.FAA:+.4f}  '
              f'HFD=[{f.HFD[0]:.3f},{f.HFD[1]:.3f},{f.HFD[2]:.3f}]')

    def on_wave(w):
        pass  # 太多不打印

    rx = BLEEEGReceiver(addr, on_wave=on_wave, on_feat=on_feat)
    rx.start()

    try:
        while True:
            time.sleep(5)
            print(f'  wave={rx.wave_count}  feat={rx.feat_count}  '
                  f'crc_err={rx.crc_errors}')
    except KeyboardInterrupt:
        rx.stop()
