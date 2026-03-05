#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVIDIA GPU 启动脚本
使用ONNX Runtime GPU进行AI推理加速
"""

import sys
import os
import signal
import time
import socket
import psutil
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_flask_app'))

def signal_handler(signum, frame):
    """信号处理器"""
    print("\n\n收到停止信号，正在关闭服务...")
    
    # 清理资源
    try:
        from my_flask_app.utils.speech_recognition_dolphin import dolphin_speech_service
        dolphin_speech_service.cleanup()
        print("✓ 语音识别服务资源清理完成 (Dolphin)")
        
        from my_flask_app.utils.emotion_recognition_gpu import gpu_emotion_service
        if gpu_emotion_service:
            gpu_emotion_service.cleanup()
            print("✓ 表情识别服务资源清理完成")
        
        # 清理MJPEG视频流服务
        try:
            from my_flask_app.utils import simple_mjpeg_stream_gpu
            if simple_mjpeg_stream_gpu:
                simple_mjpeg_stream_gpu.cleanup()
                print("✓ MJPEG视频流服务资源清理完成")
        except Exception as e:
            print(f"⚠ MJPEG服务清理失败: {e}")
        
    except Exception as e:
        print(f"⚠ 资源清理失败: {e}")
    
    print("服务已停止")
    sys.exit(0)

def check_gpu_environment():
    """检查GPU环境"""
    print("检查NVIDIA GPU环境...")
    
    gpu_status = {
        'onnxruntime_available': False,
        'cuda_available': False,
        'gpu_device_available': False,
        'models_available': False
    }
    
    # 检查ONNX Runtime
    try:
        import onnxruntime as ort
        gpu_status['onnxruntime_available'] = True
        print(f"✓ ONNX Runtime版本: {ort.__version__}")
        
        # 检查CUDA执行提供者
        providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in providers:
            gpu_status['cuda_available'] = True
            print(f"✓ CUDA执行提供者可用")
            print(f"  可用的执行提供者: {providers}")
        else:
            print(f"⚠ CUDA执行提供者不可用，将使用CPU")
            print(f"  可用的执行提供者: {providers}")
    except ImportError:
        print("⚠ ONNX Runtime未安装")
    
    # 检查PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_status['gpu_device_available'] = True
            device_count = torch.cuda.device_count()
            print(f"✓ PyTorch CUDA可用，检测到 {device_count} 个GPU设备")
            for i in range(device_count):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
                print(f"    显存: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
        else:
            print("⚠ PyTorch CUDA不可用")
    except ImportError:
        print("⚠ PyTorch未安装")
    
    # 检查模型文件（Dolphin模型会自动下载，无需检查）
    emotion_model_path = "./models/onnx_model_48.onnx"
    if os.path.exists(emotion_model_path):
        print(f"✓ 表情模型: {emotion_model_path}")
    else:
        print(f"⚠ 表情模型未找到: {emotion_model_path}")
    
    det_model_path = "./models/faceDetection.onnx"
    if not os.path.exists(det_model_path):
        det_model_path = "./models/yolov8s.onnx"
    
    if os.path.exists(det_model_path):
        print(f"✓ 人脸检测模型: {det_model_path}")
    else:
        print(f"⚠ 人脸检测模型未找到")
    
    return gpu_status

def get_system_info():
    """获取系统信息"""
    try:
        # CPU信息
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 网络信息
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        
        return {
            'cpu_cores': cpu_count,
            'cpu_usage': cpu_percent,
            'memory_total': memory.total / (1024**3),
            'memory_usage': memory.percent,
            'memory_available': memory.available / (1024**3),
            'local_ip': local_ip
        }
    except Exception as e:
        print(f"获取系统信息失败: {e}")
        return {}

def initialize_services():
    """初始化服务"""
    print("\n初始化AI服务 (GPU版本)...")
    
    success_count = 0
    
    # 初始化语音识别服务 (使用Dolphin ASR)
    try:
        from my_flask_app.utils.speech_recognition_dolphin import dolphin_speech_service
        
        print("加载语音识别模型 (Dolphin ASR)...")
        success = dolphin_speech_service.load_model()
        
        if success:
            print("✓ 语音识别服务初始化成功 (Dolphin GPU加速)")
            success_count += 1
        else:
            print("⚠ 语音识别服务初始化失败，将使用备用方案")
            
    except Exception as e:
        print(f"⚠ 语音识别服务初始化异常: {e}")
    
    # 初始化表情识别服务
    try:
        from my_flask_app.utils.emotion_recognition_gpu import gpu_emotion_service
        
        if gpu_emotion_service:
            print("加载表情识别模型 (ONNX GPU)...")
            success = gpu_emotion_service.load_model()
            
            if success:
                print("✓ 表情识别服务初始化成功 (GPU加速)")
                success_count += 1
            else:
                print("⚠ 表情识别服务初始化失败，将使用备用方案")
        else:
            print("⚠ 表情识别服务不可用")
            
    except Exception as e:
        print(f"⚠ 表情识别服务初始化异常: {e}")
    
    # 初始化MJPEG视频流服务
    try:
        from my_flask_app.utils import simple_mjpeg_stream_gpu
        
        if simple_mjpeg_stream_gpu:
            print("初始化MJPEG视频流服务 (ONNX GPU)...")
            success = simple_mjpeg_stream_gpu.load_models()
            
            if success:
                print("✓ MJPEG视频流服务初始化成功 (GPU加速)")
                success_count += 1
            else:
                print("⚠ MJPEG视频流服务初始化失败")
        else:
            print("⚠ MJPEG视频流服务不可用")
            
    except Exception as e:
        print(f"⚠ MJPEG视频流服务初始化异常: {e}")
    
    return success_count

def main():
    """主启动函数"""
    print("=" * 80)
    print("抑郁症评估系统 - NVIDIA GPU版本")
    print("=" * 80)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 获取系统信息
    print("\n系统信息:")
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"  {key}: {value}")
    
    # 检查GPU环境
    print()
    gpu_status = check_gpu_environment()
    
    # 初始化服务
    service_count = initialize_services()
    
    try:
        # 导入Flask应用
        from app import app
        
        # 显示启动信息
        print("\n" + "=" * 80)
        print("系统启动中...")
        print("=" * 80)
        
        if service_count > 0 and (gpu_status['cuda_available'] or gpu_status['onnxruntime_available']):
            print("🚀 AI加速: NVIDIA GPU (Dolphin ASR + ONNX Runtime)")
            print("⚡ 语音识别: Dolphin GPU加速推理")
            print("😊 表情识别: GPU加速推理")
            print("📹 视频流: GPU加速MJPEG")
        else:
            print("🔄 AI加速: CPU备用模式")
            print("📢 语音识别: Dolphin CPU推理")
            print("😊 表情识别: CPU标准推理")
            print("📹 视频流: 基础模式")
        
        print("💾 数据库: SQLite (嵌入式优化)")
        print(f"🌐 本机访问: http://localhost:5000")
        print(f"🌐 局域网访问: http://{system_info.get('local_ip', '127.0.0.1')}:5000")
        print("👤 默认用户: 用户名=DSH, 密码=1")
        print("=" * 80)
        
        if service_count > 0:
            print("GPU优化特性:")
            print("• NVIDIA CUDA算力加速")
            print("• Dolphin ASR 中文语音识别（GPU加速）")
            print("• ONNX Runtime GPU推理（表情识别）")
            print("• 实时语音识别推理") 
            print("• 实时表情识别推理")
            print("• 低延迟高准确率")
            print("• VAD语音活动检测支持")
        else:
            print("CPU备用特性:")
            print("• 多核心并行处理")
            print("• 内存使用优化")
            print("• 轻量级AI推理")
            print("• 兼容性保证")
        
        print("=" * 80)
        print("按 Ctrl+C 停止服务")
        print("=" * 80)
        
        # 配置Flask应用
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['ENV'] = 'production'
        
        # 启动应用
        print("🎯 系统已就绪，等待连接...")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
        
    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        print("请确保已安装所需依赖")
        print("运行: pip install -r requirements_gpu.txt")
    except Exception as e:
        print(f"\n❌ 启动错误: {e}")
        print("请检查项目文件完整性和配置")

if __name__ == "__main__":
    main()
