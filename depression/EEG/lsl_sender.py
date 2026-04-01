#!/usr/bin/env python3
"""
lsl_sender.py
-------------
Windows 采集端桥接器：把 BLE / 串口脑电数据推送为两条 LSL 流。

默认输出:
  1. EEG_Data      - 3 通道原始波形, 500Hz
  2. EEG_Features  - 10 维特征流, 1Hz

支持:
  --source ble
  --source serial
  --source mock
"""

from __future__ import annotations

import argparse
import math
import os
import random
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from ble_receiver import BLEEEGReceiver, scan_and_select
from eeg_serial import EEGSerialReceiver, FeaturePacket, WavePacket

RAW_CHANNEL_LABELS = ("F3", "F4", "Fz")
FEATURE_LABELS = (
    "FAA",
    "theta_ch0",
    "alpha_ch0",
    "beta_ch0",
    "theta_ch1",
    "alpha_ch1",
    "beta_ch1",
    "theta_ch2",
    "alpha_ch2",
    "beta_ch2",
)
ALLOWED_RESOLVE_SCOPES = {"machine", "link", "site", "organization", "global"}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_known_peers(raw_values: Sequence[str]) -> List[str]:
    peers: List[str] = []
    for raw in raw_values:
        if not raw:
            continue
        normalized = raw.replace("\n", ",").replace(";", ",")
        for part in normalized.split(","):
            candidate = part.strip()
            if candidate:
                peers.append(candidate)
    return peers


def _build_lsl_api_config(
    *,
    known_peers: Sequence[str],
    session_id: Optional[str],
    resolve_scope: Optional[str],
    disable_ipv6: bool,
) -> str:
    lines: List[str] = []

    if disable_ipv6:
        lines.extend(
            [
                "[ports]",
                "IPv6 = disable",
                "",
            ]
        )

    if resolve_scope:
        lines.extend(
            [
                "[multicast]",
                f"ResolveScope = {resolve_scope}",
                "",
            ]
        )

    if session_id or known_peers:
        lines.append("[lab]")
        if session_id:
            lines.append(f"SessionID = {session_id}")
        if known_peers:
            peers_str = ", ".join(known_peers)
            lines.append(f"KnownPeers = {{{peers_str}}}")
        lines.append("")

    return "\n".join(lines).strip() + ("\n" if lines else "")


def _prepare_lsl_runtime(
    *,
    known_peers: Sequence[str],
    session_id: Optional[str],
    resolve_scope: Optional[str],
    disable_ipv6: bool,
) -> Optional[str]:
    existing_cfg = os.getenv("LSLAPICFG")
    if existing_cfg:
        return existing_cfg

    config_text = _build_lsl_api_config(
        known_peers=known_peers,
        session_id=session_id,
        resolve_scope=resolve_scope,
        disable_ipv6=disable_ipv6,
    )
    if not config_text:
        return None

    cfg_path = os.path.join(tempfile.gettempdir(), "depression_lsl_sender.cfg")
    with open(cfg_path, "w", encoding="utf-8") as cfg_file:
        cfg_file.write(config_text)
    os.environ["LSLAPICFG"] = cfg_path
    return cfg_path


def _add_stream_metadata(info, labels: Sequence[str]):
    channels = info.desc().append_child("channels")
    for label in labels:
        channel = channels.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("type", "EEG")
        channel.append_child_value("unit", "uV")


@dataclass
class BridgeStats:
    wave_packets: int = 0
    feature_packets: int = 0
    wave_samples: int = 0
    feature_samples: int = 0


class MockEEGReceiver:
    """没有硬件时的本地冒烟测试数据源。"""

    def __init__(
        self,
        sample_rate: float,
        on_wave: Callable[[WavePacket], None],
        on_feat: Callable[[FeaturePacket], None],
    ):
        self.sample_rate = float(sample_rate)
        self.on_wave = on_wave
        self.on_feat = on_feat
        self._running = False
        self._thread = None
        self._start_ts = 0.0
        self.wave_count = 0
        self.feat_count = 0
        self.crc_errors = 0

    def start(self):
        self._running = True
        self._start_ts = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True, name="EEG-Mock")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        dt = 1.0 / max(self.sample_rate, 1.0)
        next_feature_ts = time.time()
        seq = 0

        while self._running:
            now = time.time()
            elapsed = now - self._start_ts
            wave = WavePacket(
                seq=seq,
                ch=[
                    35.0 * math.sin(2.0 * math.pi * 10.0 * elapsed) + random.uniform(-2.0, 2.0),
                    32.0 * math.sin(2.0 * math.pi * 10.5 * elapsed + 0.35) + random.uniform(-2.0, 2.0),
                    24.0 * math.sin(2.0 * math.pi * 7.0 * elapsed + 0.7) + random.uniform(-1.5, 1.5),
                ],
            )
            self.on_wave(wave)
            self.wave_count += 1
            seq = (seq + 1) % 65536

            if now >= next_feature_ts:
                alpha_left = 18.0 + 2.4 * math.sin(2.0 * math.pi * 0.13 * elapsed)
                alpha_right = 17.5 + 2.1 * math.cos(2.0 * math.pi * 0.11 * elapsed)
                alpha_mid = 14.8 + 1.4 * math.sin(2.0 * math.pi * 0.17 * elapsed)
                theta_left = 8.2 + 0.8 * math.sin(2.0 * math.pi * 0.09 * elapsed)
                theta_right = 7.6 + 0.9 * math.cos(2.0 * math.pi * 0.08 * elapsed)
                theta_mid = 7.1 + 0.7 * math.sin(2.0 * math.pi * 0.07 * elapsed)
                beta_left = 6.8 + 0.6 * math.cos(2.0 * math.pi * 0.14 * elapsed)
                beta_right = 6.5 + 0.6 * math.sin(2.0 * math.pi * 0.16 * elapsed)
                beta_mid = 5.9 + 0.5 * math.cos(2.0 * math.pi * 0.12 * elapsed)

                packet = FeaturePacket(
                    FAA=math.log(max(alpha_left, 1e-6)) - math.log(max(alpha_right, 1e-6)),
                    alpha=[alpha_left, alpha_right, alpha_mid],
                    theta=[theta_left, theta_right, theta_mid],
                    beta=[beta_left, beta_right, beta_mid],
                    APV=[0.0, 0.0, 0.0],
                    HFD=[0.0, 0.0, 0.0],
                    rsv=[0.0, 0.0],
                    timestamp=now,
                )
                self.on_feat(packet)
                self.feat_count += 1
                next_feature_ts = now + 1.0

            time.sleep(dt)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EEG -> LSL bridge sender")
    parser.add_argument("--source", choices=["ble", "serial", "mock"], default="ble", help="采集数据源")
    parser.add_argument("--address", help="BLE MAC 地址；不填则先扫描设备")
    parser.add_argument("--scan-timeout", type=float, default=5.0, help="BLE 扫描时长（秒）")
    parser.add_argument("--serial-port", help="串口端口，例如 COM3")
    parser.add_argument("--baud-rate", type=int, default=230400, help="串口波特率")
    parser.add_argument("--sample-rate", type=float, default=500.0, help="原始波形流采样率")
    parser.add_argument("--stream-name", default=os.getenv("EEG_LSL_STREAM_NAME", "EEG_Data"), help="原始波形流名称")
    parser.add_argument("--stream-type", default=os.getenv("EEG_LSL_STREAM_TYPE", "EEG"), help="原始波形流类型")
    parser.add_argument(
        "--feature-stream-name",
        default=os.getenv("EEG_LSL_FEATURE_STREAM_NAME", "EEG_Features"),
        help="特征流名称",
    )
    parser.add_argument(
        "--feature-stream-type",
        default=os.getenv("EEG_LSL_FEATURE_STREAM_TYPE", "EEG_Features"),
        help="特征流类型",
    )
    parser.add_argument("--status-interval", type=float, default=5.0, help="状态日志间隔（秒）")
    parser.add_argument("--known-peer", action="append", default=[], help="LSL KnownPeers，可重复传多次")
    parser.add_argument("--session-id", default=os.getenv("EEG_LSL_SESSION_ID"), help="LSL SessionID")
    parser.add_argument(
        "--resolve-scope",
        choices=sorted(ALLOWED_RESOLVE_SCOPES),
        default=(os.getenv("EEG_LSL_RESOLVE_SCOPE") or None),
        help="LSL ResolveScope",
    )
    parser.add_argument("--disable-ipv6", action="store_true", default=False, help="写入 LSL IPv6 disable 配置")
    parser.add_argument("--raw-source-id", help="原始波形流 source_id")
    parser.add_argument("--feature-source-id", help="特征流 source_id")
    return parser


def build_receiver(
    args: argparse.Namespace,
    *,
    on_wave: Callable[[WavePacket], None],
    on_feat: Callable[[FeaturePacket], None],
):
    if args.source == "ble":
        address = args.address
        if not address:
            address = scan_and_select(timeout=args.scan_timeout)
        if not address:
            raise RuntimeError("未选择 BLE 设备，已退出。")
        receiver = BLEEEGReceiver(address=address, on_wave=on_wave, on_feat=on_feat)
        receiver.on_status = print
        print(f"[LSL] Source: BLE {address}")
        return receiver

    if args.source == "serial":
        if not args.serial_port:
            raise RuntimeError("串口模式必须提供 --serial-port，例如 COM3。")
        print(f"[LSL] Source: serial {args.serial_port} @ {args.baud_rate}")
        return EEGSerialReceiver(
            port=args.serial_port,
            baudrate=args.baud_rate,
            on_wave=on_wave,
            on_feat=on_feat,
        )

    print("[LSL] Source: mock")
    return MockEEGReceiver(sample_rate=args.sample_rate, on_wave=on_wave, on_feat=on_feat)


def main():
    args = build_arg_parser().parse_args()

    peer_sources = list(args.known_peer)
    if not peer_sources and os.getenv("EEG_LSL_KNOWN_PEERS"):
        peer_sources.append(os.getenv("EEG_LSL_KNOWN_PEERS", ""))
    known_peers = _parse_known_peers(peer_sources)
    disable_ipv6 = bool(args.disable_ipv6 or _env_flag("EEG_LSL_DISABLE_IPV6", False))
    resolve_scope = args.resolve_scope.lower() if args.resolve_scope else None
    if resolve_scope and resolve_scope not in ALLOWED_RESOLVE_SCOPES:
        raise RuntimeError(f"不支持的 ResolveScope: {resolve_scope}")

    cfg_path = _prepare_lsl_runtime(
        known_peers=known_peers,
        session_id=(args.session_id or None),
        resolve_scope=resolve_scope,
        disable_ipv6=disable_ipv6,
    )

    from pylsl import StreamInfo, StreamOutlet, local_clock

    raw_source_id = args.raw_source_id or f"depression-eeg-raw-{args.source}"
    feature_source_id = args.feature_source_id or f"depression-eeg-feature-{args.source}"

    raw_info = StreamInfo(
        args.stream_name,
        args.stream_type,
        3,
        float(args.sample_rate),
        "float32",
        raw_source_id,
    )
    _add_stream_metadata(raw_info, RAW_CHANNEL_LABELS)
    raw_outlet = StreamOutlet(raw_info, chunk_size=1, max_buffered=360)

    feature_info = StreamInfo(
        args.feature_stream_name,
        args.feature_stream_type,
        len(FEATURE_LABELS),
        1.0,
        "float32",
        feature_source_id,
    )
    _add_stream_metadata(feature_info, FEATURE_LABELS)
    feature_outlet = StreamOutlet(feature_info, chunk_size=1, max_buffered=60)

    stats = BridgeStats()

    def on_wave(packet: WavePacket):
        raw_outlet.push_sample(list(packet.ch[:3]), local_clock())
        stats.wave_packets += 1
        stats.wave_samples += 1

    def on_feat(packet: FeaturePacket):
        sample = [
            float(packet.FAA),
            float(packet.theta[0]),
            float(packet.alpha[0]),
            float(packet.beta[0]),
            float(packet.theta[1]),
            float(packet.alpha[1]),
            float(packet.beta[1]),
            float(packet.theta[2]),
            float(packet.alpha[2]),
            float(packet.beta[2]),
        ]
        feature_outlet.push_sample(sample, local_clock())
        stats.feature_packets += 1
        stats.feature_samples += 1

    receiver = build_receiver(args, on_wave=on_wave, on_feat=on_feat)
    receiver.start()

    print(
        f"[LSL] Raw stream ready: name={args.stream_name}, type={args.stream_type}, "
        f"channels=3, srate={float(args.sample_rate):.1f}"
    )
    print(
        f"[LSL] Feature stream ready: name={args.feature_stream_name}, "
        f"type={args.feature_stream_type}, channels={len(FEATURE_LABELS)}, srate=1.0"
    )
    if known_peers:
        print(f"[LSL] KnownPeers: {', '.join(known_peers)}")
    if args.session_id:
        print(f"[LSL] SessionID: {args.session_id}")
    if resolve_scope:
        print(f"[LSL] ResolveScope: {resolve_scope}")
    if disable_ipv6:
        print("[LSL] IPv6: disable")
    if cfg_path:
        print(f"[LSL] Config file: {cfg_path}")
    print("[LSL] Streaming started. Keep this window open.")

    last_log = time.time()
    last_wave_packets = 0
    last_feature_packets = 0

    try:
        while True:
            time.sleep(0.2)
            now = time.time()
            if now - last_log >= max(args.status_interval, 0.5):
                delta_wave = stats.wave_packets - last_wave_packets
                delta_feature = stats.feature_packets - last_feature_packets
                crc_errors = getattr(receiver, "crc_errors", 0)
                print(
                    f"[LSL] wave packets={stats.wave_packets} (+{delta_wave})  "
                    f"feature packets={stats.feature_packets} (+{delta_feature})  "
                    f"crc_err={crc_errors}"
                )
                last_log = now
                last_wave_packets = stats.wave_packets
                last_feature_packets = stats.feature_packets
    except KeyboardInterrupt:
        print("\n[LSL] Stopping...")
    finally:
        receiver.stop()
        print("[LSL] Stopped.")


if __name__ == "__main__":
    main()
