# -*- coding: utf-8 -*-
"""
NVIDIA GPU表情识别服务
使用ONNX Runtime GPU进行加速推理
"""

import os
import sys
import logging
import threading
import time
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import base64
from io import BytesIO
from PIL import Image
from collections import deque

# 添加项目路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

# 尝试导入ONNX Runtime
try:
    import onnxruntime as ort
    # 屏蔽ONNX Runtime的警告信息
    ort.set_default_logger_severity(3)  # 0=Verbose, 1=Info, 2=Warning, 3=Error, 4=Fatal
    # 检查GPU是否可用
    GPU_AVAILABLE = 'CUDAExecutionProvider' in ort.get_available_providers()
    if GPU_AVAILABLE:
        print("NVIDIA GPU环境可用 - 表情识别 (ONNX Runtime)")
        print(f"可用的执行提供者: {ort.get_available_providers()}")
    else:
        print("GPU不可用，将使用CPU - 表情识别")
except ImportError as e:
    GPU_AVAILABLE = False
    print(f"ONNX Runtime不可用: {e}")
    ort = None

# === 常量配置 ===
CLASSES = {0: 'face'}
CONFIDENCE_THRES = 0.4
IOU_THRES = 0.45
EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']
EMOTION_INPUT_SIZE = (48, 48)
SMOOTHING_WINDOW_SIZE = 5


class ONNXGPUEmotionRecognitionService:
    """NVIDIA GPU表情识别服务 - 使用ONNX Runtime"""
    
    # 线程本地存储：为每个线程创建独立的模型实例
    _thread_local = threading.local()
    
    def __init__(self, device_id=0):
        """初始化GPU表情识别服务"""
        
        # 设备配置
        self.device_id = device_id
        
        # 模型路径配置 - 使用ONNX模型
        self.det_model_path = os.path.join(project_root, "models", "faceDetection.onnx")
        self.emotion_model_path = os.path.join(project_root, "models", "onnx_model_48.onnx")
        
        # 如果ONNX模型不存在，尝试使用YOLOv8的ONNX版本
        if not os.path.exists(self.det_model_path):
            # 尝试查找其他可能的ONNX模型
            alt_det_model = os.path.join(project_root, "models", "yolov8s.onnx")
            if os.path.exists(alt_det_model):
                self.det_model_path = alt_det_model
        
        # 表情类别映射
        self.emotion_labels = EMOTION_LABELS
        self.emotion_chinese = {
            'Angry': '愤怒',
            'Disgust': '厌恶',
            'Fear': '害怕',
            'Happy': '高兴',
            'Sad': '悲伤',
            'Surprise': '惊讶',
            'Neutral': '自然'
        }
        
        # 表情统计
        self.emotion_stats = {label.lower(): 0 for label in self.emotion_labels}
        self.total_detections = 0
        self._last_emotion = None  # 跟踪上次检测到的表情，用于只在变化时打印
        
        # 使用GPU模式
        self.use_gpu = GPU_AVAILABLE
        
        # 设置日志
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        # 创建日志目录
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志文件路径
        log_file = os.path.join(log_dir, 'emotion_recognition_gpu.log')
        
        # 配置日志
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 防止传播到根logger
        
        # 避免重复添加handler
        if logger.handlers:
            return
        
        # 文件handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # 控制台handler - 完全禁用所有日志输出（只通过print输出表情变化）
        # 不添加控制台handler，所有日志只写入文件
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.ERROR)
        # console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # console_handler.setFormatter(console_formatter)
        
        # 添加handlers（只添加文件handler，不添加控制台handler）
        logger.addHandler(file_handler)
        # logger.addHandler(console_handler)  # 不输出到控制台
        
        self.logger = logger
        # 只在文件中记录，不在控制台输出
        self.logger.debug(f"GPU表情识别日志已配置，日志文件: {log_file}")

    def _get_thread_sessions(self):
        """
        获取当前线程的模型实例（线程本地存储）
        每个线程都有自己独立的 ONNX Session 实例
        """
        if not hasattr(self._thread_local, 'det_session') or self._thread_local.det_session is None:
            # 为当前线程创建模型实例
            try:
                # 只在首次创建时打印一次
                if not hasattr(self, '_model_created_logged'):
                    print(f"[表情识别] 正在初始化模型（使用{'GPU' if self.use_gpu else 'CPU'}）...")
                    self._model_created_logged = True
                
                self.logger.debug(f"为线程 {threading.current_thread().name} 创建ONNX模型实例...")
                
                # 设置ONNX Runtime执行提供者
                if self.use_gpu:
                    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                    self.logger.debug("使用GPU执行提供者")
                else:
                    providers = ['CPUExecutionProvider']
                    self.logger.debug("使用CPU执行提供者")
                
                # 创建人脸检测会话
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                self._thread_local.det_session = ort.InferenceSession(
                    self.det_model_path,
                    sess_options=sess_options,
                    providers=providers
                )
                
                # 创建表情识别会话
                self._thread_local.emo_session = ort.InferenceSession(
                    self.emotion_model_path,
                    sess_options=sess_options,
                    providers=providers
                )
                
                # 为当前线程创建独立的历史记录
                self._thread_local.emotion_history = deque(maxlen=SMOOTHING_WINDOW_SIZE)
                
                self.logger.debug(f"线程 {threading.current_thread().name} ONNX模型实例创建成功")
                self.logger.debug(f"人脸检测模型提供者: {self._thread_local.det_session.get_providers()}")
                self.logger.debug(f"表情识别模型提供者: {self._thread_local.emo_session.get_providers()}")
                
            except Exception as e:
                self.logger.error(f"为线程创建ONNX模型实例失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                self._thread_local.det_session = None
                self._thread_local.emo_session = None
                self._thread_local.emotion_history = deque(maxlen=SMOOTHING_WINDOW_SIZE)
        
        return self._thread_local.det_session, self._thread_local.emo_session
    
    def _get_thread_history(self):
        """获取当前线程的表情历史记录"""
        if not hasattr(self._thread_local, 'emotion_history') or self._thread_local.emotion_history is None:
            self._thread_local.emotion_history = deque(maxlen=SMOOTHING_WINDOW_SIZE)
        return self._thread_local.emotion_history

    def preprocess_face_for_emotion(self, frame, box, target_size):
        """
        预处理人脸图像用于表情识别
        """
        x, y, w, h = box
        
        # 应用padding以获得更好的ROI
        PADDING_RATIO = 0.10
        pad_w = int(w * PADDING_RATIO)
        pad_h = int(h * PADDING_RATIO)
        
        x_min = round(x - pad_w)
        y_min = round(y - pad_h)
        x_max = round(x + w + pad_w)
        y_max = round(y + h + pad_h)
        
        # 裁剪坐标到图像边界
        x_min, y_min = max(0, x_min), max(0, y_min)
        x_max, y_max = min(frame.shape[1], x_max), min(frame.shape[0], y_max)
        
        # 裁剪人脸
        cropped_face = frame[y_min:y_max, x_min:x_max]
        
        if cropped_face.size == 0 or x_max <= x_min or y_max <= y_min:
            return None, None

        # 1. 转换为灰度图
        gray_face = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2GRAY)
        
        # 2. 调整大小到48x48
        resized_face = cv2.resize(gray_face, target_size, interpolation=cv2.INTER_LINEAR)
        
        # 3. 归一化到[0, 1]
        normalized_face = resized_face.astype(np.float32) / 255.0
        
        # 4. 转换为NCHW格式: [1, 1, 48, 48]
        input_blob = np.expand_dims(np.expand_dims(normalized_face, axis=0), axis=0)
        
        return input_blob, (x_min, y_min, x_max, y_max)

    def run_emotion_inference(self, emotion_session, face_blob):
        """
        运行表情模型推理（ONNX Runtime版本）
        """
        # ONNX Runtime推理
        input_name = emotion_session.get_inputs()[0].name
        output_name = emotion_session.get_outputs()[0].name
        
        outputs = emotion_session.run([output_name], {input_name: face_blob})
        
        # 返回logits/概率数组
        return outputs[0][0]

    def run_combined_pipeline(self, det_session, emo_session, original_image, history):
        """
        执行完整的人脸检测和表情识别流程（ONNX Runtime版本）
        """
        
        # === Phase 1: Face Detection (YOLOv8) ===
        height, width, _ = original_image.shape
        length = max(height, width)
        image = np.zeros((length, length, 3), np.uint8)
        image[0:height, 0:width] = original_image
        scale = length / 640

        blob = cv2.dnn.blobFromImage(image, scalefactor=1.0 / 255, size=(640, 640), swapRB=True)
        
        # ONNX Runtime推理
        det_input_name = det_session.get_inputs()[0].name
        det_output_name = det_session.get_outputs()[0].name
        det_outputs = det_session.run([det_output_name], {det_input_name: blob})
        
        outputs_array = np.transpose(det_outputs[0][0])
        rows = outputs_array.shape[0]
        boxes, scores, class_ids = [], [], []

        for i in range(rows):
            cls_logit = outputs_array[i][4]
            max_score = cls_logit
            max_class_index = 0
            
            if max_score >= CONFIDENCE_THRES:
                center_x, center_y, box_width, box_height = outputs_array[i][0:4]
                x_min = (center_x - box_width / 2) * scale
                y_min = (center_y - box_height / 2) * scale
                w_scaled = box_width * scale
                h_scaled = box_height * scale
                box = [x_min, y_min, w_scaled, h_scaled]
                
                boxes.append(box)
                scores.append(max_score)
                class_ids.append(max_class_index)

        indices = cv2.dnn.NMSBoxes(boxes, scores, CONFIDENCE_THRES, IOU_THRES)
        
        # 确保indices是numpy数组或列表
        if isinstance(indices, np.ndarray):
            indices = indices.flatten()
        elif indices is None:
            indices = []
        
        # === Phase 2: Local Emotion Classification ===
        detections = []
        
        if len(indices) > 0:
            for i in indices:
                # 处理numpy标量
                if hasattr(i, 'item'):
                    index = i.item()
                else:
                    index = int(i)
                box = boxes[index]
                det_class_id = class_ids[index]

                # 1. 预处理并推理表情
                face_blob, padded_coords = self.preprocess_face_for_emotion(original_image, box, EMOTION_INPUT_SIZE)
                
                if face_blob is not None and padded_coords is not None:
                    x_min, y_min, x_max, y_max = padded_coords
                    
                    # 执行ONNX推理
                    raw_scores = self.run_emotion_inference(emo_session, face_blob)
                    
                    # 转换为概率（Softmax）
                    exp_scores = np.exp(raw_scores - np.max(raw_scores))
                    probabilities = exp_scores / np.sum(exp_scores)
                    
                    # 调试日志
                    if len(probabilities) == len(EMOTION_LABELS):
                        prob_dict = {EMOTION_LABELS[i]: float(probabilities[i]) for i in range(len(EMOTION_LABELS))}
                        self.logger.debug(f"原始表情概率分布: {prob_dict}")
                    
                    # 2. 平滑和预测
                    thread_history = self._get_thread_history()
                    
                    # 轻度平滑
                    if len(thread_history) > 0:
                        history_mean = np.mean(thread_history, axis=0)
                        smoothed_probabilities = probabilities * 0.6 + history_mean * 0.4
                    else:
                        smoothed_probabilities = probabilities
                    
                    # 更新线程历史
                    thread_history.append(probabilities)
                    current_history_size = len(thread_history)
                    
                    # 3. 类别再平衡
                    balanced_prob = smoothed_probabilities.copy()
                    neutral_idx = EMOTION_LABELS.index('Neutral')
                    happy_idx = EMOTION_LABELS.index('Happy')
                    sad_idx = EMOTION_LABELS.index('Sad')
                    fear_idx = EMOTION_LABELS.index('Fear')
                    disgust_idx = EMOTION_LABELS.index('Disgust')
                    surprise_idx = EMOTION_LABELS.index('Surprise')
                    
                    # 如果Neutral过高且有其他表情存在，降低Neutral
                    max_other = max([balanced_prob[i] for i in range(len(EMOTION_LABELS)) if i != neutral_idx])
                    if balanced_prob[neutral_idx] > 0.55 and max_other > 0.12:
                        balanced_prob[neutral_idx] *= 0.7
                    
                    # Happy过高且存在负向/其他情绪时适度降低
                    if balanced_prob[happy_idx] > 0.55 and (balanced_prob[sad_idx] > 0.08 or balanced_prob[fear_idx] > 0.08):
                        balanced_prob[happy_idx] *= 0.8
                    
                    # 适度提升容易被淹没的类别
                    if balanced_prob[sad_idx] > 0.04:
                        balanced_prob[sad_idx] *= 1.6
                    if balanced_prob[fear_idx] > 0.03:
                        balanced_prob[fear_idx] *= 1.4
                    if balanced_prob[disgust_idx] > 0.02:
                        balanced_prob[disgust_idx] *= 1.4
                    if balanced_prob[surprise_idx] > 0.02:
                        balanced_prob[surprise_idx] *= 1.3
                    
                    # 重新归一化
                    balanced_prob = balanced_prob / np.sum(balanced_prob)
                    
                    # 调试日志
                    if len(smoothed_probabilities) == len(EMOTION_LABELS):
                        smoothed_dict = {EMOTION_LABELS[i]: float(smoothed_probabilities[i]) for i in range(len(EMOTION_LABELS))}
                        balanced_dict = {EMOTION_LABELS[i]: float(balanced_prob[i]) for i in range(len(EMOTION_LABELS))}
                        self.logger.debug(f"平滑后表情概率分布: {smoothed_dict}")
                        self.logger.debug(f"再平衡后表情概率分布: {balanced_dict}")
                    
                    # 使用再平衡后的概率选择表情
                    emotion_index = int(np.argmax(balanced_prob))
                    emotion_label = EMOTION_LABELS[emotion_index]
                    emotion_conf = float(balanced_prob[emotion_index])
                    
                    self.logger.debug(f"选择的表情: {emotion_label} (置信度: {emotion_conf:.3f}), 历史窗口大小: {current_history_size}")
                    
                    full_label = f"{emotion_label}:{emotion_conf:.2f}"
                    
                    # 绘制检测框和标签
                    self.draw_bounding_box(original_image, full_label, det_class_id, x_min, y_min, x_max, y_max)
                    
                    detections.append({
                        "class_id": int(det_class_id), 
                        "confidence": float(scores[index]),
                        "box": (int(x_min), int(y_min), int(x_max), int(y_max)),
                        "emotion": emotion_label.lower(),
                        "emotion_chinese": self.emotion_chinese.get(emotion_label, emotion_label),
                        "emotion_confidence": float(emotion_conf),
                        "label": full_label
                    })
                else:
                    # 使用原始box
                    x_min, y_min, x_max, y_max = round(box[0]), round(box[1]), round(box[0] + box[2]), round(box[1] + box[3])
                    full_label = "Emo Failed"
                    self.draw_bounding_box(original_image, full_label, det_class_id, x_min, y_min, x_max, y_max)
        
        # 添加模型信息文本
        cv2.putText(original_image, "MODEL: ONNX GPU", (10, height - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1, cv2.LINE_AA)
        
        return original_image, detections, self._get_thread_history()

    def draw_bounding_box(self, img, label_text, color_id, x, y, x_plus_w, y_plus_h):
        """绘制检测框和标签"""
        colors = np.array([[0, 255, 0]])  # BGR Green
        color = colors[color_id]
        
        cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color.tolist(), 2)
        
        label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_height = label_size[1]
        label_x = x
        label_y = y - 10 if y - 10 > label_height else y + 15
        
        cv2.putText(img, label_text, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 2, cv2.LINE_AA)

    def load_model(self):
        """
        加载表情识别模型（延迟加载）
        实际模型会在每个线程第一次使用时创建
        """
        try:
            self.logger.debug("检查表情识别模型文件...")
            
            # 检查模型文件
            if not os.path.exists(self.det_model_path):
                self.logger.error(f"人脸检测模型文件不存在: {self.det_model_path}")
                return False
                
            if not os.path.exists(self.emotion_model_path):
                self.logger.error(f"表情识别模型文件不存在: {self.emotion_model_path}")
                return False
            
            if ort is not None:
                self.logger.debug("模型文件检查通过，将在首次使用时为每个线程创建ONNX模型实例")
                return True
            else:
                self.logger.warning("ONNX Runtime不可用，模型无法加载")
                return False
                
        except Exception as e:
            self.logger.error(f"检查模型文件失败: {e}")
            return False

    def detect_emotion_from_image(self, image_data: str) -> Dict[str, Any]:
        """
        从base64图像数据中检测表情
        
        Args:
            image_data: base64编码的图像数据
            
        Returns:
            Dict包含检测结果
        """
        try:
            # 检查模型文件
            if not self.load_model():
                return {
                    'success': False,
                    'error': '模型文件不存在或ONNX Runtime不可用',
                    'emotions': [],
                    'dominant_emotion': 'neutral',
                    'confidence': 0.0
                }
            
            # 解码base64图像
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # 转换为OpenCV格式
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 检测表情
            if ort is not None:
                return self._detect_emotion_gpu(cv_image)
            else:
                return self._detect_emotion_cpu(cv_image)
                
        except Exception as e:
            self.logger.error(f"表情检测失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'emotions': [],
                'dominant_emotion': 'neutral',
                'confidence': 0.0
            }
    
    def _detect_emotion_gpu(self, image: np.ndarray) -> Dict[str, Any]:
        """使用GPU进行表情检测"""
        try:
            # 获取当前线程的模型实例
            det_session, emo_session = self._get_thread_sessions()
            if det_session is None or emo_session is None:
                self.logger.error("无法获取线程模型实例")
                return self._detect_emotion_cpu(image)
            
            # 执行完整流程
            try:
                draw_image, detections, history = self.run_combined_pipeline(
                    det_session, emo_session, image.copy(), None
                )
            except Exception as e:
                self.logger.error(f"run_combined_pipeline 执行失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                raise
            
            # 转换为base64图像
            try:
                success, buffer = cv2.imencode('.jpg', draw_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not success:
                    self.logger.error("图像编码失败")
                    annotated_image = None
                else:
                    image_base64 = base64.b64encode(buffer).decode('utf-8')
                    annotated_image = f"data:image/jpeg;base64,{image_base64}"
            except Exception as e:
                self.logger.error(f"图像编码异常: {e}")
                annotated_image = None
            
            # 处理检测结果
            all_emotions = []
            for det in detections:
                emotion = det.get('emotion', 'neutral')
                emotion_conf = det.get('emotion_confidence', 0.0)
                
                emotion_conf = float(emotion_conf) if emotion_conf is not None else 0.0
                
                # 更新统计
                self.emotion_stats[emotion.lower()] += 1
                self.total_detections += 1
                
                box = det.get('box')
                if box:
                    box = tuple(int(x) for x in box)
                
                all_emotions.append({
                    'emotion': str(emotion),
                    'emotion_chinese': str(det.get('emotion_chinese', emotion)),
                    'confidence': float(emotion_conf),
                    'box': box,
                    'label': str(det.get('label', ''))
                })
            
            # 确定主要表情
            if all_emotions:
                dominant = max(all_emotions, key=lambda x: x['confidence'])
                dominant_emotion = str(dominant['emotion'])
                dominant_confidence = float(dominant['confidence'])
            else:
                dominant_emotion = 'neutral'
                dominant_confidence = 0.0
            
            # 确保detections中的所有数值都是Python原生类型
            serializable_detections = []
            for det in detections:
                serializable_detections.append({
                    "class_id": int(det.get('class_id', 0)),
                    "confidence": float(det.get('confidence', 0.0)),
                    "box": tuple(int(x) for x in det.get('box', (0, 0, 0, 0))),
                    "emotion": str(det.get('emotion', 'neutral')),
                    "emotion_chinese": str(det.get('emotion_chinese', '')),
                    "emotion_confidence": float(det.get('emotion_confidence', 0.0)),
                    "label": str(det.get('label', ''))
                })
            
            result = {
                'success': True,
                'emotions': all_emotions,
                'dominant_emotion': str(dominant_emotion),
                'confidence': float(dominant_confidence),
                'faces_detected': int(len(detections)),
                'detections': serializable_detections
            }
            
            if annotated_image:
                result['annotated_image'] = annotated_image
            
            # 只在表情变化时打印
            if self._last_emotion != dominant_emotion:
                emotion_text = self.emotion_chinese.get(dominant_emotion, dominant_emotion)
                print(f"[表情检测] {emotion_text} ({dominant_confidence:.1%})")
                self._last_emotion = dominant_emotion
            
            self.logger.debug(f"检测完成: {len(detections)}个人脸, {len(all_emotions)}个表情, 主要表情: {dominant_emotion}")
            return result
                
        except Exception as e:
            self.logger.error(f"GPU表情检测失败: {e}")
            import traceback
            error_trace = traceback.format_exc()
            self.logger.error(error_trace)
            print(f"GPU表情检测异常: {e}")
            print(error_trace)
            return {
                'success': False,
                'error': f'GPU表情检测失败: {str(e)}',
                'emotions': [],
                'dominant_emotion': 'neutral',
                'confidence': 0.0,
                'faces_detected': 0
            }
    
    def _detect_emotion_cpu(self, image: np.ndarray) -> Dict[str, Any]:
        """使用CPU进行表情检测（备用方案）"""
        return {
            'success': True,
            'emotions': [],
            'dominant_emotion': 'neutral',
            'confidence': 0.5,
            'faces_detected': 0,
            'fallback': True
        }

    def get_emotion_statistics(self) -> Dict[str, Any]:
        """获取表情统计数据"""
        total = self.total_detections if self.total_detections > 0 else 1
        
        stats = {}
        for emotion, count in self.emotion_stats.items():
            stats[emotion] = {
                'count': count,
                'percentage': (count / total) * 100
            }
        
        return {
            'total_detections': self.total_detections,
            'emotions': stats,
            'most_common': max(self.emotion_stats.items(), key=lambda x: x[1])[0] if self.total_detections > 0 else 'neutral'
        }

    def reset_statistics(self):
        """重置统计数据"""
        self.emotion_stats = {label.lower(): 0 for label in self.emotion_labels}
        self.total_detections = 0
        # 重置线程历史记录
        if hasattr(self._thread_local, 'emotion_history'):
            self._thread_local.emotion_history.clear()
        self.logger.info("表情统计数据已重置")

    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        det_session, emo_session = self._get_thread_sessions()
        return {
            'model_loaded': det_session is not None and emo_session is not None,
            'gpu_available': GPU_AVAILABLE,
            'use_gpu': self.use_gpu,
            'det_model_path': self.det_model_path,
            'emotion_model_path': self.emotion_model_path,
            'emotion_labels': self.emotion_labels,
            'total_detections': self.total_detections,
            'thread_name': threading.current_thread().name
        }

    def cleanup(self):
        """清理资源"""
        try:
            # 清理线程本地存储的模型实例
            if hasattr(self._thread_local, 'det_session'):
                try:
                    del self._thread_local.det_session
                except:
                    pass
            if hasattr(self._thread_local, 'emo_session'):
                try:
                    del self._thread_local.emo_session
                except:
                    pass
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


# 创建全局服务实例
try:
    gpu_emotion_service = ONNXGPUEmotionRecognitionService()
except Exception as e:
    print(f"GPU表情识别服务初始化失败: {e}")
    gpu_emotion_service = None
