#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脑电数据接收服务

支持两种数据源：
1. serial: 直接从串口/USB 设备读取
2. lsl:    从局域网 LSL 流读取，适合 Windows 采集 + Linux 展示

当前前端页面主要使用 3 个通道的实时波形，因此 LSL 模式默认会从流中
取 3 个通道并映射到 channel1~channel3。情绪分类依赖 theta/alpha/beta
特征；如果只提供原始波形，分类接口会保持 standby，但页面画图仍可工作。
"""

import math
import os
import struct
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Sequence

try:
    import serial
except ImportError:  # pragma: no cover - optional dependency in LSL mode
    serial = None


def is_valid_float(value):
    """检查浮点数是否有效。"""
    if value is None:
        return False
    if math.isinf(value) or math.isnan(value):
        return False
    return True


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _parse_channel_map(raw_value: Optional[str]) -> List[int]:
    if not raw_value:
        return [0, 1, 2]

    try:
        values = [int(part.strip()) for part in raw_value.split(",") if part.strip()]
        if len(values) >= 3:
            return values[:3]
    except ValueError:
        pass
    return [0, 1, 2]


class EEGDataReceiver:
    """脑电数据接收器，统一提供前端所需的数据接口。"""

    def __init__(
        self,
        serial_port: Optional[str] = None,
        baud_rate: Optional[int] = None,
        source_mode: Optional[str] = None,
        lsl_stream_name: Optional[str] = None,
        lsl_stream_type: Optional[str] = None,
        lsl_channel_map: Optional[Sequence[int]] = None,
        lsl_feature_stream_name: Optional[str] = None,
        lsl_feature_stream_type: Optional[str] = None,
    ):
        env_source_mode = os.getenv("EEG_SOURCE", "serial").strip().lower()
        source_mode = (source_mode or env_source_mode).strip().lower()
        if source_mode == "auto":
            if os.getenv("EEG_LSL_STREAM_NAME") or os.getenv("EEG_LSL_FEATURE_STREAM_NAME"):
                source_mode = "lsl"
            else:
                source_mode = "serial"
        if source_mode not in {"serial", "lsl"}:
            source_mode = "serial"

        self.source_mode = source_mode

        self.serial_port = serial_port or os.getenv("EEG_SERIAL_PORT", "/dev/ttyUSB0")
        self.baud_rate = baud_rate or _env_int("EEG_BAUD_RATE", 230400)
        self.ser = None

        self.lsl_stream_name = lsl_stream_name or os.getenv("EEG_LSL_STREAM_NAME", "EEG_Data")
        self.lsl_stream_type = lsl_stream_type or os.getenv("EEG_LSL_STREAM_TYPE", "EEG")
        self.lsl_channel_map = list(
            lsl_channel_map if lsl_channel_map is not None else _parse_channel_map(os.getenv("EEG_LSL_CHANNEL_MAP"))
        )
        self.lsl_feature_stream_name = lsl_feature_stream_name or os.getenv("EEG_LSL_FEATURE_STREAM_NAME")
        self.lsl_feature_stream_type = lsl_feature_stream_type or os.getenv("EEG_LSL_FEATURE_STREAM_TYPE", "EEG_Features")
        self.lsl_resolve_timeout = _env_float("EEG_LSL_RESOLVE_TIMEOUT", 2.0)
        self.lsl_pull_timeout = _env_float("EEG_LSL_PULL_TIMEOUT", 0.2)

        self.running = False
        self.thread = None
        self.feature_thread = None

        self.source_connected = False
        self.last_source_error = ""
        self.last_data_timestamp = 0.0
        self._last_wait_log: Dict[str, float] = {}

        # 原始数据缓存（保留最近约 4 秒 @500Hz）
        self.channels_data = {
            1: {"values": deque(maxlen=2000), "timestamps": deque(maxlen=2000)},
            2: {"values": deque(maxlen=2000), "timestamps": deque(maxlen=2000)},
            3: {"values": deque(maxlen=2000), "timestamps": deque(maxlen=2000)},
        }

        # 特征数据（theta/alpha/beta）
        self.features_data = {
            1: {
                "current": {"theta": None, "alpha": None, "beta": None, "timestamp": 0},
                "history": {
                    "theta": deque(maxlen=100),
                    "alpha": deque(maxlen=100),
                    "beta": deque(maxlen=100),
                    "timestamps": deque(maxlen=100),
                },
            },
            2: {
                "current": {"theta": None, "alpha": None, "beta": None, "timestamp": 0},
                "history": {
                    "theta": deque(maxlen=100),
                    "alpha": deque(maxlen=100),
                    "beta": deque(maxlen=100),
                    "timestamps": deque(maxlen=100),
                },
            },
            3: {
                "current": {"theta": None, "alpha": None, "beta": None, "timestamp": 0},
                "history": {
                    "theta": deque(maxlen=100),
                    "alpha": deque(maxlen=100),
                    "beta": deque(maxlen=100),
                    "timestamps": deque(maxlen=100),
                },
            },
        }

        self.latest_data = {
            "channel": 0,
            "value": 0.0,
            "theta": None,
            "alpha": None,
            "beta": None,
            "timestamp": 0.0,
            "source": self.source_mode,
        }
        self.stream_buffer = deque(maxlen=4000)

        self.lock = threading.Lock()

        self.stats = {
            "total_packets": 0,
            "data_packets": 0,
            "feature_packets": 0,
            "invalid_packets": 0,
        }

        # 情绪推理配置
        self.emotion_thresholds = {
            "T_ASYM": 0.1,
            "T_BT_POS": 0.7,
            "T_BT_NEG": 0.3,
            "MIN_SCORE": 0.2,
            "WINDOW_SEC": 4.0,
            "MIN_DATA_POINTS": 3,
        }

        self.emotion_result_cache = {
            "label": "standby",
            "score": 0.0,
            "window_sec": 4.0,
            "timestamp": 0,
            "features": {
                "alpha_left": None,
                "alpha_right": None,
                "beta_left": None,
                "beta_right": None,
                "theta_left": None,
                "theta_right": None,
                "alpha_log_left": None,
                "alpha_log_right": None,
                "fai": None,
                "beta_theta_left": None,
                "beta_theta_right": None,
            },
            "reason": "initializing",
        }
        self.emotion_lock = threading.Lock()
        self.emotion_thread = None
        self.emotion_running = False

        self._init_crc_table()

    def _init_crc_table(self):
        self._crc_table = [0] * 256
        poly = 0x1021
        for i in range(256):
            crc = i << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
            self._crc_table[i] = crc & 0xFFFF

    def calculate_crc16_nrf(self, data: bytes):
        crc = 0xFFFF
        for byte in data:
            idx = ((crc >> 8) ^ byte) & 0xFF
            crc = ((crc << 8) ^ self._crc_table[idx]) & 0xFFFF
        return crc

    def start(self):
        """启动接收线程和情绪推理线程。"""
        if self.running:
            print("[EEG] 接收器已在运行")
            return True

        self.running = True

        try:
            if self.source_mode == "lsl":
                try:
                    import pylsl  # noqa: F401
                except ImportError as exc:
                    raise RuntimeError("pylsl 未安装，无法使用 LSL 模式") from exc

                self.thread = threading.Thread(target=self._lsl_wave_loop, daemon=True, name="EEG-LSL-Wave")
                self.thread.start()

                if self.lsl_feature_stream_name or os.getenv("EEG_LSL_FEATURE_STREAM_NAME"):
                    self.feature_thread = threading.Thread(
                        target=self._lsl_feature_loop,
                        daemon=True,
                        name="EEG-LSL-Feature",
                    )
                    self.feature_thread.start()
            else:
                if serial is None:
                    raise RuntimeError("pyserial 未安装，无法使用 serial 模式")
                self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=0.1)
                self.ser.reset_input_buffer()
                self.thread = threading.Thread(target=self._receive_loop_serial, daemon=True, name="EEG-Serial-RX")
                self.thread.start()

            self._start_emotion_inference()

            print("[EEG] 脑电接收器已启动")
            print(f"  数据源: {self.source_mode}")
            if self.source_mode == "serial":
                print(f"  端口: {self.serial_port}")
                print(f"  波特率: {self.baud_rate}")
            else:
                print(f"  LSL波形流: name={self.lsl_stream_name}, type={self.lsl_stream_type}")
                if self.lsl_feature_stream_name:
                    print(f"  LSL特征流: name={self.lsl_feature_stream_name}, type={self.lsl_feature_stream_type}")
                print(f"  LSL通道映射: {self.lsl_channel_map}")
            print("[EEG] 情绪推理线程已启动（1000ms更新频率）")
            return True

        except Exception as e:
            self.running = False
            self.last_source_error = str(e)
            print(f"[EEG] 启动失败: {e}")
            return False

    def stop(self):
        self.running = False
        self.source_connected = False

        self._stop_emotion_inference()

        if self.thread:
            self.thread.join(timeout=2.0)
        if self.feature_thread:
            self.feature_thread.join(timeout=2.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        print("[EEG] 接收器已停止")

    def _append_wave_sample(self, ch_id: int, raw_val: float, timestamp: Optional[float] = None):
        if ch_id < 1 or ch_id > 3 or not is_valid_float(raw_val):
            with self.lock:
                self.stats["invalid_packets"] += 1
            return

        current_time = float(timestamp or time.time())
        with self.lock:
            self.channels_data[ch_id]["values"].append(raw_val)
            self.channels_data[ch_id]["timestamps"].append(current_time)
            current_features = self.features_data[ch_id]["current"].copy()
            self.latest_data = {
                "channel": ch_id,
                "value": raw_val,
                "theta": current_features["theta"],
                "alpha": current_features["alpha"],
                "beta": current_features["beta"],
                "timestamp": current_time,
                "source": self.source_mode,
            }
            self.stream_buffer.append(
                {
                    "type": "raw",
                    "channel": ch_id,
                    "value": raw_val,
                    "timestamp": current_time,
                    "source": self.source_mode,
                }
            )
            self.stats["data_packets"] += 1
            self.stats["total_packets"] += 1
            self.last_data_timestamp = current_time

    def _append_feature_sample(
        self,
        ch_id: int,
        theta: float,
        alpha: float,
        beta: float,
        timestamp: Optional[float] = None,
    ):
        if ch_id < 1 or ch_id > 3:
            with self.lock:
                self.stats["invalid_packets"] += 1
            return

        if not (is_valid_float(theta) and is_valid_float(alpha) and is_valid_float(beta)):
            with self.lock:
                self.stats["invalid_packets"] += 1
            return

        current_time = float(timestamp or time.time())
        with self.lock:
            self.features_data[ch_id]["current"] = {
                "theta": theta,
                "alpha": alpha,
                "beta": beta,
                "timestamp": current_time,
            }
            history = self.features_data[ch_id]["history"]
            history["theta"].append(theta)
            history["alpha"].append(alpha)
            history["beta"].append(beta)
            history["timestamps"].append(current_time)
            self.stream_buffer.append(
                {
                    "type": "feature",
                    "channel": ch_id,
                    "theta": theta,
                    "alpha": alpha,
                    "beta": beta,
                    "timestamp": current_time,
                    "source": self.source_mode,
                }
            )
            self.stats["feature_packets"] += 1
            self.stats["total_packets"] += 1

    def _receive_loop_serial(self):
        """串口接收循环。"""
        print("[EEG] 串口接收循环已启动")
        buffer = b""

        while self.running:
            try:
                if self.ser.in_waiting:
                    buffer += self.ser.read(self.ser.in_waiting)

                while len(buffer) >= 3:
                    if buffer[0] != 0x06 or buffer[1] != 0x09:
                        buffer = buffer[1:]
                        continue

                    pkt_type = buffer[2]
                    if pkt_type == 0x01:
                        target_len = 10
                    elif pkt_type == 0x02:
                        target_len = 18
                    else:
                        buffer = buffer[2:]
                        continue

                    if len(buffer) < target_len:
                        break

                    frame = buffer[:target_len]
                    calc_crc = self.calculate_crc16_nrf(frame[:-2])
                    recv_crc = (frame[-2] << 8) | frame[-1]

                    if calc_crc != recv_crc:
                        with self.lock:
                            self.stats["invalid_packets"] += 1
                        buffer = buffer[1:]
                        continue

                    buffer = buffer[target_len:]
                    ch_id = int(frame[3])

                    if pkt_type == 0x01:
                        raw_val = struct.unpack("<f", frame[4:8])[0]
                        self._append_wave_sample(ch_id, raw_val)
                    else:
                        theta = struct.unpack("<f", frame[4:8])[0]
                        alpha = struct.unpack("<f", frame[8:12])[0]
                        beta = struct.unpack("<f", frame[12:16])[0]
                        self._append_feature_sample(ch_id, theta, alpha, beta)

                self.source_connected = True
                self.last_source_error = ""

            except Exception as e:
                if self.running:
                    self.source_connected = False
                    self.last_source_error = str(e)
                    print(f"[EEG] 串口接收错误: {e}")
                    time.sleep(0.05)

            if self.running and self.ser and not self.ser.in_waiting and len(buffer) < 3:
                time.sleep(0.001)

    def _maybe_log_waiting(self, label: str, message: str, interval_sec: float = 5.0):
        now = time.time()
        last_time = self._last_wait_log.get(label, 0.0)
        if now - last_time >= interval_sec:
            print(message)
            self._last_wait_log[label] = now

    def _resolve_lsl_stream(self, stream_name: Optional[str], stream_type: Optional[str], label: str, min_channels: int):
        from pylsl import resolve_byprop

        while self.running:
            streams = []
            if stream_name:
                streams = resolve_byprop("name", stream_name, minimum=1, timeout=self.lsl_resolve_timeout)

            if not streams and stream_type:
                streams = resolve_byprop("type", stream_type, minimum=1, timeout=self.lsl_resolve_timeout)

            if streams:
                for stream in streams:
                    try:
                        if stream.channel_count() >= min_channels:
                            return stream
                    except Exception:
                        return stream
                return streams[0]

            self._maybe_log_waiting(label, f"[EEG][LSL] 等待 {label} 流: name={stream_name or '-'}, type={stream_type or '-'}")

        return None

    def _lsl_wave_loop(self):
        """LSL 波形流接收循环。"""
        try:
            from pylsl import StreamInlet
        except ImportError as exc:
            self.last_source_error = "pylsl 未安装"
            self.running = False
            print(f"[EEG][LSL] 启动失败: {exc}")
            return

        while self.running:
            inlet = None
            try:
                stream = self._resolve_lsl_stream(
                    stream_name=self.lsl_stream_name,
                    stream_type=self.lsl_stream_type,
                    label="EEG原始波形",
                    min_channels=max(self.lsl_channel_map) + 1,
                )
                if stream is None:
                    return

                inlet = StreamInlet(stream, max_buflen=2, recover=True)
                self.source_connected = True
                self.last_source_error = ""
                print("[EEG][LSL] 已连接原始波形流")

                while self.running:
                    sample, timestamp = inlet.pull_sample(timeout=self.lsl_pull_timeout)
                    if sample is None:
                        continue
                    self._handle_lsl_wave_sample(sample, timestamp)

            except Exception as e:
                if self.running:
                    self.source_connected = False
                    self.last_source_error = str(e)
                    print(f"[EEG][LSL] 波形流错误: {e}")
                    time.sleep(1.0)
            finally:
                if inlet is not None:
                    self.source_connected = False

    def _lsl_feature_loop(self):
        """可选的 LSL 特征流接收循环。"""
        try:
            from pylsl import StreamInlet
        except ImportError as exc:
            self.last_source_error = "pylsl 未安装"
            print(f"[EEG][LSL] 特征流不可用: {exc}")
            return

        while self.running:
            try:
                stream = self._resolve_lsl_stream(
                    stream_name=self.lsl_feature_stream_name,
                    stream_type=self.lsl_feature_stream_type,
                    label="EEG特征",
                    min_channels=9,
                )
                if stream is None:
                    return

                inlet = StreamInlet(stream, max_buflen=2, recover=True)
                print("[EEG][LSL] 已连接特征流")

                while self.running:
                    sample, timestamp = inlet.pull_sample(timeout=self.lsl_pull_timeout)
                    if sample is None:
                        continue
                    self._handle_lsl_feature_sample(sample, timestamp)

            except Exception as e:
                if self.running:
                    print(f"[EEG][LSL] 特征流错误: {e}")
                    time.sleep(1.0)

    def _handle_lsl_wave_sample(self, sample: Sequence[float], timestamp: Optional[float]):
        if len(sample) <= max(self.lsl_channel_map):
            with self.lock:
                self.stats["invalid_packets"] += 1
            return

        sample_timestamp = float(timestamp or time.time())
        for ch_id, source_index in enumerate(self.lsl_channel_map, start=1):
            try:
                raw_val = float(sample[source_index])
            except (TypeError, ValueError, IndexError):
                with self.lock:
                    self.stats["invalid_packets"] += 1
                continue
            self._append_wave_sample(ch_id, raw_val, sample_timestamp)

    def _handle_lsl_feature_sample(self, sample: Sequence[float], timestamp: Optional[float]):
        sample_len = len(sample)
        if sample_len < 9:
            with self.lock:
                self.stats["invalid_packets"] += 1
            return

        # 支持 9 维 [theta,alpha,beta] * 3，或 10 维 [FAA + 9维特征]
        offset = 1 if sample_len >= 10 and (sample_len - 1) >= 9 else 0
        if sample_len - offset < 9:
            with self.lock:
                self.stats["invalid_packets"] += 1
            return

        sample_timestamp = float(timestamp or time.time())
        for ch_id in range(1, 4):
            base = offset + (ch_id - 1) * 3
            try:
                theta = float(sample[base])
                alpha = float(sample[base + 1])
                beta = float(sample[base + 2])
            except (TypeError, ValueError, IndexError):
                with self.lock:
                    self.stats["invalid_packets"] += 1
                continue
            self._append_feature_sample(ch_id, theta, alpha, beta, sample_timestamp)

    def get_latest_data(self):
        with self.lock:
            latest = self.latest_data.copy()
        latest["theta"] = 0.0 if latest["theta"] is None else latest["theta"]
        latest["alpha"] = 0.0 if latest["alpha"] is None else latest["alpha"]
        latest["beta"] = 0.0 if latest["beta"] is None else latest["beta"]
        return latest

    def get_history_data(self, channel: int = 1, max_points: int = 500):
        with self.lock:
            values = list(self.channels_data.get(channel, {"values": []})["values"])[-max_points:]
            timestamps = list(self.channels_data.get(channel, {"timestamps": []})["timestamps"])[-max_points:]
        return {"channel": channel, "values": values, "timestamps": timestamps}

    def get_stream_data(self, max_items: int = 120):
        batch = []
        with self.lock:
            while self.stream_buffer and len(batch) < max_items:
                batch.append(self.stream_buffer.popleft())
        return batch

    def get_channel_data(self, channel):
        with self.lock:
            if channel in self.channels_data:
                return {
                    "values": list(self.channels_data[channel]["values"]),
                    "timestamps": list(self.channels_data[channel]["timestamps"]),
                }
            return {"values": [], "timestamps": []}

    def get_channel_features(self, channel):
        with self.lock:
            if channel in self.features_data:
                return {
                    "current": self.features_data[channel]["current"].copy(),
                    "history": {
                        "theta": list(self.features_data[channel]["history"]["theta"]),
                        "alpha": list(self.features_data[channel]["history"]["alpha"]),
                        "beta": list(self.features_data[channel]["history"]["beta"]),
                        "timestamps": list(self.features_data[channel]["history"]["timestamps"]),
                    },
                }
            return {
                "current": {"theta": None, "alpha": None, "beta": None, "timestamp": 0},
                "history": {"theta": [], "alpha": [], "beta": [], "timestamps": []},
            }

    def get_all_channels_data(self):
        with self.lock:
            result = {
                "channel1": {
                    "waveform": list(self.channels_data[1]["values"]),
                    "timestamps": list(self.channels_data[1]["timestamps"]),
                    "features": {
                        "current": self.features_data[1]["current"].copy(),
                        "history": {
                            "theta": list(self.features_data[1]["history"]["theta"]),
                            "alpha": list(self.features_data[1]["history"]["alpha"]),
                            "beta": list(self.features_data[1]["history"]["beta"]),
                            "timestamps": list(self.features_data[1]["history"]["timestamps"]),
                        },
                    },
                },
                "channel2": {
                    "waveform": list(self.channels_data[2]["values"]),
                    "timestamps": list(self.channels_data[2]["timestamps"]),
                    "features": {
                        "current": self.features_data[2]["current"].copy(),
                        "history": {
                            "theta": list(self.features_data[2]["history"]["theta"]),
                            "alpha": list(self.features_data[2]["history"]["alpha"]),
                            "beta": list(self.features_data[2]["history"]["beta"]),
                            "timestamps": list(self.features_data[2]["history"]["timestamps"]),
                        },
                    },
                },
                "channel3": {
                    "waveform": list(self.channels_data[3]["values"]),
                    "timestamps": list(self.channels_data[3]["timestamps"]),
                    "features": {
                        "current": self.features_data[3]["current"].copy(),
                        "history": {
                            "theta": list(self.features_data[3]["history"]["theta"]),
                            "alpha": list(self.features_data[3]["history"]["alpha"]),
                            "beta": list(self.features_data[3]["history"]["beta"]),
                            "timestamps": list(self.features_data[3]["history"]["timestamps"]),
                        },
                    },
                },
                "stats": self.stats.copy(),
                "source": self.get_source_status(),
            }

        return result

    def _start_emotion_inference(self):
        if self.emotion_running:
            return

        self.emotion_running = True
        self.emotion_thread = threading.Thread(
            target=self._emotion_inference_loop,
            daemon=True,
            name="EEG-Emotion-Inference",
        )
        self.emotion_thread.start()
        print("[EEG Emotion] 推理线程已启动")

    def _stop_emotion_inference(self):
        self.emotion_running = False
        if self.emotion_thread:
            self.emotion_thread.join(timeout=2.0)
        print("[EEG Emotion] 推理线程已停止")

    def _emotion_inference_loop(self):
        while self.emotion_running:
            try:
                result = self._compute_emotion_classification()
                with self.emotion_lock:
                    self.emotion_result_cache = result
            except Exception as e:
                print(f"[EEG Emotion] 推理错误: {e}")
            time.sleep(1.0)

    def _mean_recent(self, values, timestamps, window_sec):
        if not values or not timestamps:
            return None

        now = time.time()
        start_time = now - window_sec
        acc = []

        for i, ts in enumerate(timestamps):
            if ts >= start_time and i < len(values):
                val = values[i]
                if val is not None and not math.isnan(val) and not math.isinf(val):
                    acc.append(val)

        if not acc:
            return None

        return sum(acc) / len(acc)

    def _compute_emotion_classification(self):
        window_sec = self.emotion_thresholds["WINDOW_SEC"]
        T_ASYM = self.emotion_thresholds["T_ASYM"]
        T_BT_POS = self.emotion_thresholds["T_BT_POS"]
        T_BT_NEG = self.emotion_thresholds["T_BT_NEG"]
        MIN_SCORE = self.emotion_thresholds["MIN_SCORE"]
        MIN_DATA_POINTS = self.emotion_thresholds["MIN_DATA_POINTS"]
        eps = 1e-6

        with self.lock:
            hist = {
                1: {
                    "history": {
                        "alpha": list(self.features_data[1]["history"]["alpha"]),
                        "beta": list(self.features_data[1]["history"]["beta"]),
                        "theta": list(self.features_data[1]["history"]["theta"]),
                        "timestamps": list(self.features_data[1]["history"]["timestamps"]),
                    }
                },
                2: {
                    "history": {
                        "alpha": list(self.features_data[2]["history"]["alpha"]),
                        "beta": list(self.features_data[2]["history"]["beta"]),
                        "theta": list(self.features_data[2]["history"]["theta"]),
                        "timestamps": list(self.features_data[2]["history"]["timestamps"]),
                    }
                },
            }

        alpha_l = self._mean_recent(hist[1]["history"]["alpha"], hist[1]["history"]["timestamps"], window_sec)
        beta_l = self._mean_recent(hist[1]["history"]["beta"], hist[1]["history"]["timestamps"], window_sec)
        theta_l = self._mean_recent(hist[1]["history"]["theta"], hist[1]["history"]["timestamps"], window_sec)

        alpha_r = self._mean_recent(hist[2]["history"]["alpha"], hist[2]["history"]["timestamps"], window_sec)
        beta_r = self._mean_recent(hist[2]["history"]["beta"], hist[2]["history"]["timestamps"], window_sec)
        theta_r = self._mean_recent(hist[2]["history"]["theta"], hist[2]["history"]["timestamps"], window_sec)

        ts_left = hist[1]["history"]["timestamps"]
        ts_right = hist[2]["history"]["timestamps"]

        def count_recent(ts_list):
            now = time.time()
            start = now - window_sec
            return sum(1 for item in ts_list if item >= start)

        left_cnt = count_recent(ts_left)
        right_cnt = count_recent(ts_right)

        if left_cnt < MIN_DATA_POINTS or right_cnt < MIN_DATA_POINTS:
            return {
                "label": "standby",
                "score": 0.0,
                "window_sec": window_sec,
                "timestamp": time.time(),
                "features": {
                    "alpha_left": alpha_l,
                    "alpha_right": alpha_r,
                    "beta_left": beta_l,
                    "beta_right": beta_r,
                    "theta_left": theta_l,
                    "theta_right": theta_r,
                    "alpha_log_left": None,
                    "alpha_log_right": None,
                    "fai": None,
                    "beta_theta_left": None,
                    "beta_theta_right": None,
                },
                "reason": "insufficient_data",
            }

        def safe_ratio(a, b):
            if a is None or b is None:
                return None
            if abs(b) < 1e-30:
                return None
            return a / b

        def safe_log(x):
            if x is None or x <= 0:
                return None
            return math.log(x)

        bt_left = safe_ratio(beta_l, theta_l)
        bt_right = safe_ratio(beta_r, theta_r)

        log_alpha_l = safe_log(alpha_l)
        log_alpha_r = safe_log(alpha_r)
        fai = None
        if log_alpha_l is not None and log_alpha_r is not None:
            fai = log_alpha_l - log_alpha_r

        if fai is None or bt_left is None or bt_right is None:
            return {
                "label": "standby",
                "score": 0.0,
                "window_sec": window_sec,
                "timestamp": time.time(),
                "features": {
                    "alpha_left": alpha_l,
                    "alpha_right": alpha_r,
                    "beta_left": beta_l,
                    "beta_right": beta_r,
                    "theta_left": theta_l,
                    "theta_right": theta_r,
                    "alpha_log_left": log_alpha_l,
                    "alpha_log_right": log_alpha_r,
                    "fai": fai,
                    "beta_theta_left": bt_left,
                    "beta_theta_right": bt_right,
                },
                "reason": "invalid_feature",
            }

        pos_score = 0.0
        neg_score = 0.0

        if fai > T_ASYM:
            pos_score += min(1.0, fai / T_ASYM) * 0.4
        if fai < -T_ASYM:
            neg_score += min(1.0, abs(fai) / T_ASYM) * 0.4

        if bt_left > T_BT_POS and bt_right > T_BT_POS:
            pos_score += min(1.0, min(bt_left, bt_right) / T_BT_POS) * 0.6
        if bt_left < T_BT_NEG and bt_right < T_BT_NEG:
            neg_score += min(1.0, T_BT_NEG / max(bt_left, bt_right, eps)) * 0.6

        if pos_score > neg_score and pos_score > MIN_SCORE:
            label = "positive"
            score = min(1.0, pos_score)
        elif neg_score > pos_score and neg_score > MIN_SCORE:
            label = "negative"
            score = min(1.0, neg_score)
        else:
            label = "neutral"
            score = 0.5

        return {
            "label": label,
            "score": round(float(score), 4),
            "window_sec": window_sec,
            "timestamp": time.time(),
            "features": {
                "alpha_left": alpha_l,
                "alpha_right": alpha_r,
                "beta_left": beta_l,
                "beta_right": beta_r,
                "theta_left": theta_l,
                "theta_right": theta_r,
                "alpha_log_left": log_alpha_l,
                "alpha_log_right": log_alpha_r,
                "fai": fai,
                "beta_theta_left": bt_left,
                "beta_theta_right": bt_right,
            },
            "reason": "ok",
        }

    def get_emotion_classification(self, window_sec=4.0):
        with self.emotion_lock:
            result = self.emotion_result_cache.copy()
            if window_sec != result.get("window_sec"):
                result["window_sec"] = window_sec
            return result

    def get_source_status(self):
        return {
            "source_mode": self.source_mode,
            "connected": self.source_connected,
            "last_error": self.last_source_error,
            "last_data_timestamp": self.last_data_timestamp,
        }

    def get_stats(self):
        with self.lock:
            stats = self.stats.copy()
        stats.update(self.get_source_status())
        return stats


eeg_receiver = None


def get_eeg_receiver():
    global eeg_receiver
    if eeg_receiver is None:
        eeg_receiver = EEGDataReceiver()
        try:
            eeg_receiver.start()
        except Exception as e:
            print(f"[EEG] 无法启动脑电接收器: {e}")
    return eeg_receiver


if __name__ == "__main__":
    receiver = EEGDataReceiver()
    if receiver.start():
        print("接收器已启动，按 Ctrl+C 停止...")
        try:
            while True:
                stats = receiver.get_stats()
                print(
                    f"\n统计: 总包={stats['total_packets']}, 数据包={stats['data_packets']}, "
                    f"特征包={stats['feature_packets']}, 无效={stats['invalid_packets']}, "
                    f"source={stats['source_mode']}, connected={stats['connected']}"
                )
                latest = receiver.get_latest_data()
                print(
                    f"  Latest: ch={latest['channel']}, value={latest['value']:.4f}, "
                    f"theta={latest['theta']:.4f}, alpha={latest['alpha']:.4f}, beta={latest['beta']:.4f}"
                )
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n停止接收...")
            receiver.stop()
