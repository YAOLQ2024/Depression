# -*- coding: utf-8 -*-
"""
NVIDIA GPU版MJPEG视频流
使用ONNX Runtime GPU进行加速推理
"""

import cv2
import numpy as np
import os
import sys
from collections import deque

# 添加项目路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

# 导入ONNX Runtime
try:
    import onnxruntime as ort
    # 屏蔽ONNX Runtime的警告信息
    ort.set_default_logger_severity(3)  # 0=Verbose, 1=Info, 2=Warning, 3=Error, 4=Fatal
    GPU_AVAILABLE = 'CUDAExecutionProvider' in ort.get_available_providers()
    if GPU_AVAILABLE:
        print("[SimpleMJPEG_GPU] NVIDIA GPU环境可用")
    else:
        print("[SimpleMJPEG_GPU] GPU不可用，将使用CPU")
except ImportError as e:
    GPU_AVAILABLE = False
    print(f"[SimpleMJPEG_GPU] ONNX Runtime不可用: {e}")
    ort = None

# === 常量配置 ===
CONFIDENCE_THRES = 0.4
IOU_THRES = 0.45
EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']
EMOTION_INPUT_SIZE = (48, 48)
SMOOTHING_WINDOW_SIZE = 5

# 表情中文映射
EMOTION_CHINESE = {
    'Angry': '愤怒', 'Disgust': '厌恶', 'Fear': '害怕',
    'Happy': '高兴', 'Sad': '悲伤', 'Surprise': '惊讶', 'Neutral': '自然'
}

# 模型路径 - 使用ONNX模型
DET_MODEL_PATH = os.path.join(project_root, "models", "faceDetection.onnx")
EMOTION_MODEL_PATH = os.path.join(project_root, "models", "onnx_model_48.onnx")

# 如果ONNX模型不存在，尝试其他路径
if not os.path.exists(DET_MODEL_PATH):
    alt_det_model = os.path.join(project_root, "models", "yolov8s.onnx")
    if os.path.exists(alt_det_model):
        DET_MODEL_PATH = alt_det_model

# 全局变量 - 模型会话（单例）
_det_session = None
_emo_session = None
_model_loaded = False

# 全局摄像头对象
_global_cap = None
_stream_active = False

# 全局统计
emotion_stats = {label.lower(): 0 for label in EMOTION_LABELS}
total_detections = 0


def load_models():
    """加载模型（单例模式，只加载一次）"""
    global _det_session, _emo_session, _model_loaded
    
    # 检查模型是否已加载且会话对象有效
    if _model_loaded and _det_session is not None and _emo_session is not None:
        print("[SimpleMJPEG_GPU] 模型已加载，跳过")
        return True
    
    if ort is None:
        print("[SimpleMJPEG_GPU] ONNX Runtime不可用")
        return False
    
    try:
        # 如果之前的会话还存在，先清理
        if _det_session is not None:
            print("[SimpleMJPEG_GPU] 清理旧的人脸检测会话")
            del _det_session
            _det_session = None
        
        if _emo_session is not None:
            print("[SimpleMJPEG_GPU] 清理旧的表情识别会话")
            del _emo_session
            _emo_session = None
        
        print(f"[SimpleMJPEG_GPU] 加载人脸检测模型: {DET_MODEL_PATH}")
        if not os.path.exists(DET_MODEL_PATH):
            print(f"[SimpleMJPEG_GPU] 模型文件不存在: {DET_MODEL_PATH}")
            return False
        
        print(f"[SimpleMJPEG_GPU] 加载表情识别模型: {EMOTION_MODEL_PATH}")
        if not os.path.exists(EMOTION_MODEL_PATH):
            print(f"[SimpleMJPEG_GPU] 模型文件不存在: {EMOTION_MODEL_PATH}")
            return False
        
        # 设置ONNX Runtime执行提供者
        if GPU_AVAILABLE:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            print("[SimpleMJPEG_GPU] 使用GPU执行提供者")
        else:
            providers = ['CPUExecutionProvider']
            print("[SimpleMJPEG_GPU] 使用CPU执行提供者")
        
        # 创建会话选项
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # 创建ONNX推理会话
        _det_session = ort.InferenceSession(
            DET_MODEL_PATH,
            sess_options=sess_options,
            providers=providers
        )
        
        _emo_session = ort.InferenceSession(
            EMOTION_MODEL_PATH,
            sess_options=sess_options,
            providers=providers
        )
        
        _model_loaded = True
        
        print("[SimpleMJPEG_GPU] 模型加载成功！")
        print(f"[SimpleMJPEG_GPU] 人脸检测模型提供者: {_det_session.get_providers()}")
        print(f"[SimpleMJPEG_GPU] 表情识别模型提供者: {_emo_session.get_providers()}")
        return True
        
    except Exception as e:
        print(f"[SimpleMJPEG_GPU] 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        _model_loaded = False
        return False


def preprocess_face_for_emotion(frame, box, target_size):
    """预处理人脸图像用于表情识别"""
    x, y, w, h = box
    
    PADDING_RATIO = 0.10
    pad_w = int(w * PADDING_RATIO)
    pad_h = int(h * PADDING_RATIO)
    
    x_min = round(x - pad_w)
    y_min = round(y - pad_h)
    x_max = round(x + w + pad_w)
    y_max = round(y + h + pad_h)
    
    x_min, y_min = max(0, x_min), max(0, y_min)
    x_max, y_max = min(frame.shape[1], x_max), min(frame.shape[0], y_max)
    
    cropped_face = frame[y_min:y_max, x_min:x_max]
    
    if cropped_face.size == 0 or x_max <= x_min or y_max <= y_min:
        return None, None
    
    gray_face = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2GRAY)
    resized_face = cv2.resize(gray_face, target_size, interpolation=cv2.INTER_LINEAR)
    normalized_face = resized_face.astype(np.float32) / 255.0
    input_blob = np.expand_dims(np.expand_dims(normalized_face, axis=0), axis=0)
    
    return input_blob, (x_min, y_min, x_max, y_max)


def run_emotion_inference(emotion_session, face_blob):
    """运行表情推理（ONNX Runtime版本）"""
    input_name = emotion_session.get_inputs()[0].name
    output_name = emotion_session.get_outputs()[0].name
    
    outputs = emotion_session.run([output_name], {input_name: face_blob})
    return outputs[0][0]


def draw_bounding_box(img, label_text, color_id, x, y, x_plus_w, y_plus_h):
    """绘制检测框"""
    colors = np.array([[0, 255, 0]])
    color = colors[color_id]
    
    cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color.tolist(), 2)
    
    label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    label_height = label_size[1]
    label_x = x
    label_y = y - 10 if y - 10 > label_height else y + 15
    
    cv2.putText(img, label_text, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (255, 255, 255), 2, cv2.LINE_AA)


def run_combined_pipeline(det_session, emo_session, original_image, history):
    """
    执行完整的人脸检测和表情识别流程（ONNX Runtime GPU版本）
    """
    global emotion_stats, total_detections
    
    height, width, _ = original_image.shape
    length = max(height, width)
    image = np.zeros((length, length, 3), np.uint8)
    image[0:height, 0:width] = original_image
    scale = length / 640

    blob = cv2.dnn.blobFromImage(image, scalefactor=1.0 / 255, size=(640, 640), swapRB=True)
    
    # ONNX Runtime推理 - 人脸检测
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
    
    detections = []
    
    if len(indices) > 0:
        for i in indices:
            index = i.item() if hasattr(i, 'item') else int(i)
            box = boxes[index]
            det_class_id = class_ids[index]

            face_blob, padded_coords = preprocess_face_for_emotion(original_image, box, EMOTION_INPUT_SIZE)
            
            if face_blob is not None and padded_coords is not None:
                x_min, y_min, x_max, y_max = padded_coords
                
                # ONNX Runtime推理 - 表情识别
                raw_scores = run_emotion_inference(emo_session, face_blob)
                
                exp_scores = np.exp(raw_scores - np.max(raw_scores))
                probabilities = exp_scores / np.sum(exp_scores)
                
                history.append(probabilities)
                smoothed_probabilities = np.mean(history, axis=0)
                
                emotion_index = np.argmax(smoothed_probabilities)
                emotion_label = EMOTION_LABELS[emotion_index]
                emotion_conf = smoothed_probabilities[emotion_index]
                
                # 更新统计
                emotion_stats[emotion_label.lower()] += 1
                total_detections += 1
                
                full_label = f"{emotion_label}:{emotion_conf:.2f}"
            else:
                x_min, y_min, x_max, y_max = round(box[0]), round(box[1]), round(box[0] + box[2]), round(box[1] + box[3])
                full_label = "Emo Failed"
            
            detections.append({
                "class_id": det_class_id, 
                "confidence": scores[index], 
                "box": (x_min, y_min, x_max, y_max), 
                "emotion": full_label
            })
            
            draw_bounding_box(original_image, full_label, det_class_id, x_min, y_min, x_max, y_max)
    
    # 添加模型信息
    model_text = "GPU MJPEG" if GPU_AVAILABLE else "CPU MJPEG"
    cv2.putText(original_image, model_text, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1, cv2.LINE_AA)
        
    return original_image, detections, history


def stop_stream():
    """主动停止流并释放摄像头"""
    global _global_cap, _stream_active, _det_session, _emo_session, _model_loaded
    
    _stream_active = False
    
    if _global_cap is not None:
        try:
            _global_cap.release()
            print("[SimpleMJPEG_GPU] 摄像头已主动释放")
        except:
            pass
        _global_cap = None
    
    # 清理ONNX会话
    try:
        if _det_session is not None:
            del _det_session
            _det_session = None
            print("[SimpleMJPEG_GPU] 人脸检测会话已清理")
        
        if _emo_session is not None:
            del _emo_session
            _emo_session = None
            print("[SimpleMJPEG_GPU] 表情识别会话已清理")
        
        _model_loaded = False
    except Exception as e:
        print(f"[SimpleMJPEG_GPU] 清理ONNX会话失败: {e}")
    
    print("[SimpleMJPEG_GPU] 视频流已停止")


def generate_mjpeg_frames():
    """
    生成MJPEG视频流帧 - NVIDIA GPU版本
    
    关键优化：
    1. 使用全局摄像头对象，避免重复打开
    2. 使用 cap.grab() + cap.retrieve() 确保获取最新帧
    3. 不使用 sleep，让循环自然运行
    4. 单线程处理，避免同步问题
    """
    global _det_session, _emo_session, _global_cap, _stream_active
    
    print("[SimpleMJPEG_GPU] generate_mjpeg_frames() 被调用")
    
    # 如果之前的流还在运行，先停止
    if _stream_active:
        print("[SimpleMJPEG_GPU] 检测到旧的流还在运行，先停止...")
        stop_stream()
        import time
        time.sleep(0.8)
    
    # 加载模型
    if not load_models():
        print("[SimpleMJPEG_GPU] 模型加载失败，返回错误帧")
        error_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Model Load Failed", (30, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        _, buffer = cv2.imencode('.jpg', error_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        return
    
    # 初始化摄像头
    CAMERA_SOURCE = 0
    WIDTH = 320
    HEIGHT = 240
    
    # 如果摄像头已经被占用，先释放
    if _global_cap is not None:
        print("[SimpleMJPEG_GPU] 检测到摄像头已打开，先释放...")
        try:
            _global_cap.release()
        except:
            pass
        _global_cap = None
        import time
        time.sleep(0.5)
    
    # 打开摄像头
    _global_cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not _global_cap.isOpened():
        # 检查系统中可用的摄像头设备
        import glob
        video_devices = glob.glob('/dev/video*')
        if not video_devices:
            print(f"[SimpleMJPEG_GPU] 摄像头打开失败: 系统中未找到摄像头设备 (/dev/video* 不存在)")
            print(f"[SimpleMJPEG_GPU] 可能的原因: 1) 摄像头未连接 2) 摄像头驱动未加载 3) 权限不足")
        else:
            print(f"[SimpleMJPEG_GPU] 摄像头打开失败: 无法打开索引 {CAMERA_SOURCE} 的摄像头")
            print(f"[SimpleMJPEG_GPU] 系统中找到的摄像头设备: {video_devices}")
            print(f"[SimpleMJPEG_GPU] 提示: 尝试检查摄像头是否被其他程序占用，或尝试其他摄像头索引")
        
        error_frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camera Error", (60, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(error_frame, "No Camera Found", (30, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        _, buffer = cv2.imencode('.jpg', error_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        _global_cap = None
        return
    
    # 摄像头优化设置
    _global_cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    _global_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    try:
        _global_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        _global_cap.set(cv2.CAP_PROP_FPS, 30.0)
        _global_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except:
        pass
    
    print("[SimpleMJPEG_GPU] 开始视频流生成...")
    _stream_active = True
    
    # 表情历史记录
    emotion_history = deque(maxlen=SMOOTHING_WINDOW_SIZE)
    
    # JPEG编码参数
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
    
    # 帧计数器
    frame_count = 0
    
    try:
        # 主循环
        while _stream_active:
            # 关键优化：先grab丢弃旧帧，再retrieve获取最新帧
            _global_cap.grab()
            success, frame = _global_cap.retrieve()
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[SimpleMJPEG_GPU] 已处理 {frame_count} 帧")
            
            if not success:
                # 如果retrieve失败，尝试普通read
                success, frame = _global_cap.read()
                if not success:
                    continue
            
            # 运行完整的检测流程
            draw_image, detections, emotion_history = run_combined_pipeline(
                _det_session, _emo_session, frame, emotion_history
            )
            
            # 编码为JPEG并输出
            success_encode, buffer = cv2.imencode('.jpg', draw_image, encode_params)
            
            if success_encode:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
    except GeneratorExit:
        print("[SimpleMJPEG_GPU] 客户端断开连接")
    except Exception as e:
        print(f"[SimpleMJPEG_GPU] 流生成错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if _global_cap is not None:
            _global_cap.release()
            _global_cap = None
        _stream_active = False
        print("[SimpleMJPEG_GPU] 摄像头已释放")


def get_statistics():
    """获取统计数据"""
    global emotion_stats, total_detections
    
    total = max(1, total_detections)
    stats = {}
    for emotion, count in emotion_stats.items():
        stats[emotion] = {
            'count': count,
            'percentage': (count / total) * 100
        }
    
    return {
        'total_detections': total_detections,
        'emotions': stats,
        'most_common': max(emotion_stats.items(), key=lambda x: x[1])[0] if total_detections > 0 else 'neutral'
    }


def reset_statistics():
    """重置统计"""
    global emotion_stats, total_detections
    emotion_stats = {label.lower(): 0 for label in EMOTION_LABELS}
    total_detections = 0
    print("[SimpleMJPEG_GPU] 统计数据已重置")


def cleanup():
    """清理资源"""
    global _det_session, _emo_session, _model_loaded
    
    try:
        if _det_session:
            del _det_session
            _det_session = None
        if _emo_session:
            del _emo_session
            _emo_session = None
        _model_loaded = False
        print("[SimpleMJPEG_GPU] 资源已清理")
    except Exception as e:
        print(f"[SimpleMJPEG_GPU] 清理失败: {e}")
