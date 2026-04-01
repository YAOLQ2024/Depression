"""
eeg_serial.py
-------------
串口协议解析：匹配 nRF52832 UART 输出格式
  波形包: [06][09][01][seq:2B][ch0~2: 12B][CRC16:2B]  = 19 B @ 500Hz
  特征包: [06][09][02][FAA+APV+beta+HFD+alpha+theta+rsv: 72B][CRC16:2B] = 77 B @ ~1Hz
"""

import math
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import serial

# ═══════════════════════ 常量 ═══════════════════════
SYNC = bytes([0x06, 0x09])
PKT_TYPE_WAVE = 0x01
PKT_TYPE_FEAT = 0x02
WAVE_TOTAL = 19
FEAT_TOTAL = 77
NUM_CH = 3

# ═══════════════════════ CRC16-CCITT ═══════════════════════
_CRC_TABLE: List[int] = []


def _build_crc_table():
    global _CRC_TABLE
    _CRC_TABLE = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
        _CRC_TABLE.append(crc)


_build_crc_table()


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc = ((crc << 8) ^ _CRC_TABLE[(crc >> 8) ^ b]) & 0xFFFF
    return crc


# ═══════════════════════ 特征名 ═══════════════════════

RAW_FEAT_NAMES = [
    "FAA",
    "APV_ch0",
    "APV_ch1",
    "APV_ch2",
    "beta_ch0",
    "beta_ch1",
    "beta_ch2",
    "HFD_ch0",
    "HFD_ch1",
    "HFD_ch2",
    "alpha_ch0",
    "alpha_ch1",
    "alpha_ch2",
    "theta_ch0",
    "theta_ch1",
    "theta_ch2",
]

DERIVED_FEAT_NAMES = [
    "theta_alpha_r0",
    "theta_alpha_r1",
    "theta_alpha_r2",
    "FBA",
    "rel_alpha_ch0",
    "rel_alpha_ch1",
    "rel_alpha_ch2",
    "theta_beta_mid",
]

ALL_FEAT_NAMES = RAW_FEAT_NAMES + DERIVED_FEAT_NAMES


# ═══════════════════════ 数据结构 ═══════════════════════


@dataclass
class WavePacket:
    seq: int = 0
    ch: List[float] = field(default_factory=lambda: [0.0] * NUM_CH)


@dataclass
class FeaturePacket:
    """与 STM32 FeatureResult_t 一一对应。"""

    FAA: float = 0.0
    APV: List[float] = field(default_factory=lambda: [0.0] * NUM_CH)
    beta: List[float] = field(default_factory=lambda: [0.0] * NUM_CH)
    HFD: List[float] = field(default_factory=lambda: [0.0] * NUM_CH)
    alpha: List[float] = field(default_factory=lambda: [0.0] * NUM_CH)
    theta: List[float] = field(default_factory=lambda: [0.0] * NUM_CH)
    rsv: List[float] = field(default_factory=lambda: [0.0] * 2)
    timestamp: float = 0.0

    def to_vector(self) -> List[float]:
        """导出 24 维特征向量（16 原始 + 8 衍生）。"""
        raw = [self.FAA] + self.APV + self.beta + self.HFD + self.alpha + self.theta
        derived = compute_derived_features(self.alpha, self.beta, self.theta)
        return raw + derived


def compute_derived_features(alpha: List[float], beta: List[float], theta: List[float]) -> List[float]:
    """
    从 alpha/beta/theta 功率计算 8 个衍生特征。
    输入: 各为 3 元素 list [ch0, ch1, ch2]
    输出: 8 元素 list
    """
    eps = 1e-12

    theta_alpha_r = [theta[c] / max(alpha[c], eps) for c in range(3)]

    b_left = max(beta[0], eps)
    b_right = max(beta[1], eps)
    fba = math.log(b_right) - math.log(b_left)

    rel_alpha = []
    for c in range(3):
        total = theta[c] + alpha[c] + beta[c]
        rel_alpha.append(alpha[c] / max(total, eps))

    theta_beta_mid = theta[2] / max(beta[2], eps)

    return theta_alpha_r + [fba] + rel_alpha + [theta_beta_mid]


# ═══════════════════════ 解析器 ═══════════════════════


def _parse_feat_payload(payload: bytes) -> Optional[FeaturePacket]:
    if len(payload) != 72:
        return None
    vals = struct.unpack("<18f", payload)
    fp = FeaturePacket(timestamp=time.time())
    fp.FAA = vals[0]
    fp.APV = list(vals[1:4])
    fp.beta = list(vals[4:7])
    fp.HFD = list(vals[7:10])
    fp.alpha = list(vals[10:13])
    fp.theta = list(vals[13:16])
    fp.rsv = list(vals[16:18])
    return fp


class EEGSerialReceiver:
    def __init__(
        self,
        port: str,
        baudrate: int = 230400,
        on_wave: Optional[Callable[[WavePacket], None]] = None,
        on_feat: Optional[Callable[[FeaturePacket], None]] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.on_wave = on_wave
        self.on_feat = on_feat
        self._ser = None
        self._thread = None
        self._running = False
        self.wave_count = 0
        self.feat_count = 0
        self.crc_errors = 0

    def start(self):
        self._ser = serial.Serial(self.port, self.baudrate, timeout=0.5)
        self._ser.reset_input_buffer()
        self._running = True
        self._thread = threading.Thread(target=self._rx_loop, daemon=True, name="EEG-RX")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._ser and self._ser.is_open:
            self._ser.close()

    def _rx_loop(self):
        buf = bytearray()
        while self._running:
            try:
                chunk = self._ser.read(max(1, self._ser.in_waiting))
            except Exception:
                break
            if not chunk:
                continue
            buf.extend(chunk)

            while len(buf) >= 3:
                idx = buf.find(SYNC)
                if idx < 0:
                    buf = buf[-1:]
                    break
                if idx > 0:
                    buf = buf[idx:]

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

                raw = bytes(buf[:pkt_len])
                buf = buf[pkt_len:]

                crc_calc = crc16_ccitt(raw[:-2])
                crc_recv = (raw[-2] << 8) | raw[-1]
                if crc_calc != crc_recv:
                    self.crc_errors += 1
                    continue

                if ptype == PKT_TYPE_WAVE and self.on_wave:
                    seq = struct.unpack("<H", raw[3:5])[0]
                    chs = list(struct.unpack("<3f", raw[5:17]))
                    self.on_wave(WavePacket(seq=seq, ch=chs))
                    self.wave_count += 1

                elif ptype == PKT_TYPE_FEAT and self.on_feat:
                    fp = _parse_feat_payload(raw[3:75])
                    if fp:
                        self.on_feat(fp)
                        self.feat_count += 1


if __name__ == "__main__":
    import sys

    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"

    def _on_feat(packet: FeaturePacket):
        vector = packet.to_vector()
        print(
            f"[FEAT] {len(vector)}维  FAA={packet.FAA:+.4f}  "
            f"HFD=[{packet.HFD[0]:.3f},{packet.HFD[1]:.3f},{packet.HFD[2]:.3f}]"
        )

    receiver = EEGSerialReceiver(port, on_feat=_on_feat)
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
