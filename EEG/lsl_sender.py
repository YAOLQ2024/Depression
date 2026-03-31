"""
将 Windows 采集端的 EEG 数据桥接为局域网 LSL 流。

支持两种输入：
1. BLE: 复用 ble_receiver.py 连接脑电帽
2. serial: 复用 eeg_serial.py 连接串口/USB 设备

输出两个 LSL 流：
1. 波形流 EEG_Data      -> 3 通道原始波形
2. 特征流 EEG_Features  -> [FAA + theta/alpha/beta * 3]

示例：
    python lsl_sender.py --source ble
    python lsl_sender.py --source ble --address AA:BB:CC:DD:EE:FF
    python lsl_sender.py --source serial --port COM5
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from typing import Optional

from ble_receiver import BLEEEGReceiver, scan_and_select
from eeg_serial import EEGSerialReceiver, FeaturePacket, WavePacket


DEFAULT_WAVE_STREAM_NAME = "EEG_Data"
DEFAULT_WAVE_STREAM_TYPE = "EEG"
DEFAULT_FEATURE_STREAM_NAME = "EEG_Features"
DEFAULT_FEATURE_STREAM_TYPE = "EEG_Features"
DEFAULT_LSL_SESSION_ID = "depression-eeg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge EEG data to LAN LSL streams.")
    parser.add_argument("--source", choices=["ble", "serial"], default="ble", help="Acquisition source.")
    parser.add_argument("--address", help="BLE device address. If omitted in BLE mode, scan and choose interactively.")
    parser.add_argument("--port", default="COM5", help="Serial port in serial mode, e.g. COM5.")
    parser.add_argument("--baudrate", type=int, default=230400, help="Serial baudrate.")
    parser.add_argument("--wave-stream-name", default=DEFAULT_WAVE_STREAM_NAME, help="LSL raw-wave stream name.")
    parser.add_argument("--wave-stream-type", default=DEFAULT_WAVE_STREAM_TYPE, help="LSL raw-wave stream type.")
    parser.add_argument("--feature-stream-name", default=DEFAULT_FEATURE_STREAM_NAME, help="LSL feature stream name.")
    parser.add_argument("--feature-stream-type", default=DEFAULT_FEATURE_STREAM_TYPE, help="LSL feature stream type.")
    parser.add_argument("--wave-rate", type=float, default=500.0, help="Nominal sampling rate for the wave stream.")
    parser.add_argument("--disable-feature-stream", action="store_true", help="Send only the raw wave stream.")
    parser.add_argument("--known-peer", action="append", default=[], help="Known peer IP/hostname. Repeatable. Useful when multicast discovery fails.")
    parser.add_argument("--session-id", default=DEFAULT_LSL_SESSION_ID, help="Shared LSL session id for sender/receiver.")
    parser.add_argument("--resolve-scope", choices=["machine", "link", "site", "organization", "global"], default="machine", help="LSL resolve scope.")
    parser.add_argument("--disable-ipv6", action="store_true", help="Disable IPv6 for liblsl to avoid bad virtual/VPN interfaces.")
    parser.add_argument("--lsl-config", help="Use an existing lsl_api.cfg file instead of generating one.")
    return parser


def configure_lsl_runtime(args: argparse.Namespace) -> Optional[str]:
    if args.lsl_config:
        os.environ["LSLAPICFG"] = args.lsl_config
        print(f"[LSL] Using config file: {args.lsl_config}")
        return args.lsl_config

    known_peers = [peer.strip() for peer in args.known_peer if peer and peer.strip()]
    needs_config = bool(known_peers or args.session_id or args.disable_ipv6 or args.resolve_scope)
    if not needs_config:
        return None

    lines = []
    if args.disable_ipv6:
        lines.extend([
            "[ports]",
            "IPv6 = disable",
            "",
        ])

    if args.resolve_scope:
        lines.extend([
            "[multicast]",
            f"ResolveScope = {args.resolve_scope}",
            "",
        ])

    if known_peers or args.session_id:
        lines.append("[lab]")
        if known_peers:
            lines.append("KnownPeers = {" + ", ".join(known_peers) + "}")
        if args.session_id:
            lines.append(f"SessionID = {args.session_id}")
        lines.append("")

    config_path = os.path.join(tempfile.gettempdir(), "depression_lsl_sender.cfg")
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")

    os.environ["LSLAPICFG"] = config_path
    print(f"[LSL] Generated config: {config_path}")
    print(open(config_path, "r", encoding="utf-8").read().strip())
    return config_path


def create_wave_outlet(pylsl_module, stream_name: str, stream_type: str, sample_rate: float):
    info = pylsl_module.StreamInfo(stream_name, stream_type, 3, sample_rate, "float32", "depression-eeg-wave")
    channels = info.desc().append_child("channels")
    for label in ("F3", "F4", "Fpz"):
        channel = channels.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("unit", "uV")
        channel.append_child_value("type", "EEG")
    return pylsl_module.StreamOutlet(info, chunk_size=1, max_buffered=360)


def create_feature_outlet(pylsl_module, stream_name: str, stream_type: str):
    info = pylsl_module.StreamInfo(stream_name, stream_type, 10, 1.0, "float32", "depression-eeg-feature")
    channels = info.desc().append_child("channels")
    for label in (
        "FAA",
        "theta_ch0", "alpha_ch0", "beta_ch0",
        "theta_ch1", "alpha_ch1", "beta_ch1",
        "theta_ch2", "alpha_ch2", "beta_ch2",
    ):
        channel = channels.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("type", "EEGFeature")
    return pylsl_module.StreamOutlet(info, chunk_size=1, max_buffered=120)


def main() -> int:
    args = build_parser().parse_args()
    configure_lsl_runtime(args)
    from pylsl import local_clock
    import pylsl

    wave_outlet = create_wave_outlet(pylsl, args.wave_stream_name, args.wave_stream_type, args.wave_rate)
    feature_outlet = None
    if not args.disable_feature_stream:
        feature_outlet = create_feature_outlet(pylsl, args.feature_stream_name, args.feature_stream_type)

    print("[LSL] Raw stream ready:")
    print(f"      name={args.wave_stream_name} type={args.wave_stream_type} rate={args.wave_rate}")
    if feature_outlet:
        print("[LSL] Feature stream ready:")
        print(f"      name={args.feature_stream_name} type={args.feature_stream_type}")

    state = {
        "wave_count": 0,
        "feature_count": 0,
        "started_at": time.time(),
    }

    def on_wave(packet: WavePacket):
        wave_outlet.push_sample([float(packet.ch[0]), float(packet.ch[1]), float(packet.ch[2])], local_clock())
        state["wave_count"] += 1
        if state["wave_count"] % 500 == 0:
            elapsed = max(time.time() - state["started_at"], 1e-6)
            print(f"[LSL] wave packets={state['wave_count']} avg_rate={state['wave_count'] / elapsed:.1f}Hz")

    def on_feat(packet: FeaturePacket):
        if feature_outlet is None:
            return
        sample = [
            float(packet.FAA),
            float(packet.theta[0]), float(packet.alpha[0]), float(packet.beta[0]),
            float(packet.theta[1]), float(packet.alpha[1]), float(packet.beta[1]),
            float(packet.theta[2]), float(packet.alpha[2]), float(packet.beta[2]),
        ]
        feature_outlet.push_sample(sample, local_clock())
        state["feature_count"] += 1
        if state["feature_count"] % 5 == 0:
            print(
                "[LSL] feature packets=%d FAA=%+.4f theta/alpha/beta(ch0)=%.4f/%.4f/%.4f"
                % (
                    state["feature_count"],
                    packet.FAA,
                    packet.theta[0],
                    packet.alpha[0],
                    packet.beta[0],
                )
            )

    if args.source == "ble":
        address = args.address or scan_and_select()
        if not address:
            print("[LSL] No BLE device selected.")
            return 1
        receiver = BLEEEGReceiver(address, on_wave=on_wave, on_feat=on_feat)
        print(f"[LSL] Connecting BLE device: {address}")
    else:
        receiver = EEGSerialReceiver(args.port, baudrate=args.baudrate, on_wave=on_wave, on_feat=on_feat)
        print(f"[LSL] Opening serial port: {args.port} @ {args.baudrate}")

    receiver.start()

    print("[LSL] Streaming started. Keep this window open.")
    print("[LSL] Linux side should subscribe to the stream over the same LAN.")

    try:
        while True:
            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\n[LSL] Stopping...")
    finally:
        receiver.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
