#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dolphin 语音识别服务
使用Dolphin ASR模型进行语音识别，支持GPU加速
替代原有的ONNX Runtime方案
"""

import os
import sys
import tempfile
import logging
import time
import numpy as np
import torch
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
sys.path.insert(0, project_root)

# 导入dolphin库
try:
    import dolphin
    DOLPHIN_AVAILABLE = True
    print("✓ Dolphin ASR库可用")
except ImportError as e:
    DOLPHIN_AVAILABLE = False
    print(f"✗ Dolphin ASR库不可用: {e}")
    dolphin = None

# 检查GPU可用性
GPU_AVAILABLE = torch.cuda.is_available()
if GPU_AVAILABLE:
    print(f"✓ CUDA GPU可用 - {torch.cuda.get_device_name(0)}")
else:
    print("⚠ GPU不可用，将使用CPU进行语音识别")


class DolphinSpeechRecognitionService:
    """
    Dolphin语音识别服务
    使用Dolphin ASR模型进行语音识别，支持GPU加速
    """
    
    def __init__(self):
        # 模型配置
        self.model_size = "small"  # 可选: tiny, small, medium, large
        self.model_dir = os.path.join(project_root, "models", "dolphin")
        self.device = "cuda" if GPU_AVAILABLE else "cpu"
        
        # 音频参数
        self.sample_rate = 16000
        
        # 模型实例
        self.model = None
        
        # 设置日志
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        # 创建日志目录
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'speech_recognition_dolphin.log')
        
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if logger.handlers:
            self.logger = logger
            return
        
        # 文件handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        self.logger = logger
        self.logger.info(f"Dolphin语音识别日志已配置，日志文件: {log_file}")

    def load_model(self):
        """加载语音识别模型"""
        try:
            self.logger.info("开始加载Dolphin ASR模型...")
            
            # 检查dolphin库
            if not DOLPHIN_AVAILABLE:
                self.logger.error("Dolphin库不可用，无法加载模型")
                return False
            
            # 创建模型目录
            if not os.path.exists(self.model_dir):
                os.makedirs(self.model_dir)
                self.logger.info(f"创建模型目录: {self.model_dir}")
            
            # 加载模型
            self.logger.info(f"加载模型 '{self.model_size}' 到 {self.device}...")
            self.model = dolphin.load_model(self.model_size, self.model_dir, self.device)
            
            self.logger.info(f"✓ Dolphin ASR模型加载成功 (设备: {self.device})")
            return True
                
        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def normalize_audio(self, audio_data):
        """
        标准化音频（放大音量），使其峰值达到 0.9
        """
        if len(audio_data) == 0:
            return audio_data
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return audio_data / max_val * 0.9
        return audio_data

    def transcribe_audio(self, audio_data_or_path) -> str:
        """
        语音转文字
        :param audio_data_or_path: 音频文件路径或音频字节数据
        :return: 识别的文本
        """
        try:
            self.logger.info("开始语音识别...")
            
            # 确保模型已加载
            if self.model is None:
                if not self.load_model():
                    return ""
            
            # 处理音频数据
            wav_file = None
            temp_file = None
            
            if isinstance(audio_data_or_path, (bytes, bytearray)):
                # 如果是字节数据，先保存为临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(audio_data_or_path)
                    wav_file = tmp_file.name
                    temp_file = wav_file
            elif isinstance(audio_data_or_path, str):
                # 如果是文件路径
                wav_file = audio_data_or_path
            else:
                self.logger.error("不支持的音频数据格式")
                return ""
            
            # 加载音频文件
            import torchaudio
            waveform, sample_rate = torchaudio.load(wav_file)
            
            # 重采样到16kHz（如果需要）
            if sample_rate != self.sample_rate:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, 
                    new_freq=self.sample_rate
                )
                waveform = resampler(waveform)
            
            # 转换为单声道
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # 压缩到1D
            waveform = waveform.squeeze()
            
            # 标准化音频（提高识别率）
            audio_np = waveform.numpy()
            audio_np = self.normalize_audio(audio_np)
            waveform = torch.from_numpy(audio_np)
            
            # 移动到正确的设备
            if self.device == "cuda":
                waveform = waveform.cuda()
            
            # 执行识别
            t0 = time.time()
            result = self.model(waveform, lang_sym="zh", region_sym="SHANGHAI")
            text = result.text.strip()
            
            elapsed = time.time() - t0
            self.logger.info(f"语音识别完成 [{elapsed:.2f}s]: {text}")
            
            # 清理临时文件
            if temp_file:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            return text
            
        except Exception as e:
            self.logger.error(f"语音识别失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return ""

    def extract_answer_from_text(self, text: str) -> Optional[str]:
        """
        从识别的文本中提取SDS量表的答案选项
        """
        if not text:
            return None

        text = text.lower().strip()
        
        # 答案匹配规则
        answer_patterns = {
            'A': [
                'a', 'A', '选a', '选择a', 'a选项', '第一项', '第一选项',
                '1', '一', '第一', '第一个', '1选项', '选1', '第1', '壹',
                '没有', '极少', '没有时间', '极少时间', '一点都没有',
                '完全没有', '几乎没有', '从来没有', '从不', '不会',
                '不是', '没感觉', '完全不', '最少', '最轻', '基本没有',
                '无', '零'
            ],
            'B': [
                'b', 'B', '选b', '选择b', 'b选项', '第二项', '第二选项',
                '2', '二', '第二', '第二个', '2选项', '选2', '第2', '贰',
                '少部分', '少部分时间', '少量', '有时', '偶尔',
                '小部分', '有时候', '偶尔有', '不多', '一点点',
                '较少', '轻微', '稍微', '一些', '少许'
            ],
            'C': [
                'c', 'C', '选c', '选择c', 'c选项', '第三项', '第三选项',
                '3', '三', '第三', '第三个', '3选项', '选3', '第3', '叁',
                '相当多', '相当多时间', '很多', '经常', '大部分',
                '较多', '经常有', '常常', '大多数', '大部分时间',
                '比较多', '中等', '明显', '较重', '频繁'
            ],
            'D': [
                'd', 'D', '选d', '选择d', 'd选项', '第四项', '第四选项',
                '4', '四', '第四', '第四个', '4选项', '选4', '第4', '肆',
                '全部', '全部时间', '所有', '总是', '完全',
                '绝大部分', '绝大部分时间', '一直', '始终',
                '每天', '全天', '最多', '最重', '严重', '非常',
                '持续', '不断'
            ]
        }

        # 计算匹配得分
        scores = {}
        for option, patterns in answer_patterns.items():
            scores[option] = 0
            for pattern in patterns:
                if pattern in text:
                    if text == pattern:
                        scores[option] += 10
                    elif pattern.startswith('选') or pattern.endswith('选项'):
                        scores[option] += 8
                    elif pattern.isdigit() or pattern in ['一', '二', '三', '四', '壹', '贰', '叁', '肆']:
                        scores[option] += 6
                    elif len(pattern) >= 3:
                        scores[option] += 4
                    elif len(pattern) == 2:
                        scores[option] += 2
                    else:
                        scores[option] += 1

        # 找到最高得分
        max_score = max(scores.values()) if scores.values() else 0
        if max_score == 0:
            return None

        # 返回最高得分的选项
        best_options = [option for option, score in scores.items() if score == max_score]
        return sorted(best_options)[0] if best_options else None

    def process_speech_for_sds(self, audio_data_or_path) -> Dict[str, Any]:
        """
        处理SDS量表的语音输入
        """
        try:
            start_time = time.time()
            
            # 语音转文字
            text = self.transcribe_audio(audio_data_or_path)
            
            if not text:
                return {
                    'answer': None,
                    'confidence': 0,
                    'text': '',
                    'message': '未识别到有效语音内容，请重试',
                    'processing_time': time.time() - start_time,
                    'gpu_used': GPU_AVAILABLE and self.model is not None
                }

            # 提取答案选项
            answer = self.extract_answer_from_text(text)

            # 计算置信度
            base_confidence = 0.9 if (GPU_AVAILABLE and self.model is not None) else 0.7
            confidence = base_confidence if answer else 0.2

            processing_time = time.time() - start_time

            return {
                'answer': answer,
                'confidence': confidence,
                'text': text,
                'message': f'识别到选项: {answer}' if answer else '无法确定选项，请尝试更清楚地表达',
                'processing_time': processing_time,
                'gpu_used': GPU_AVAILABLE and self.model is not None,
                'suggestions': [
                    '请尝试说："选择A"、"选B"、"我选C"等',
                    '或直接说数字："1"、"二"、"第三个"等',
                    '或说出对应含义："没有"、"偶尔"、"经常"、"总是"等'
                ] if not answer else None
            }

        except Exception as e:
            self.logger.error(f"处理语音输入失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'answer': None,
                'confidence': 0,
                'text': '',
                'message': f'语音识别失败: {str(e)}',
                'processing_time': 0,
                'gpu_used': False
            }

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'model_loaded': self.model is not None,
            'gpu_available': GPU_AVAILABLE,
            'dolphin_available': DOLPHIN_AVAILABLE,
            'model_size': self.model_size,
            'model_dir': self.model_dir,
            'device': self.device
        }

    def cleanup(self):
        """清理资源"""
        try:
            if self.model:
                # 清理模型资源
                self.model = None
                # 清理GPU缓存
                if GPU_AVAILABLE:
                    torch.cuda.empty_cache()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


# 创建全局服务实例
dolphin_speech_service = DolphinSpeechRecognitionService()

