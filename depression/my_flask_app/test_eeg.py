#!/usr/bin/env python3
"""测试脑电数据接收器"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask_app.utils.eeg_receiver import EEGDataReceiver
import time

print("=" * 70)
print("脑电数据接收器测试")
print("=" * 70)

# 创建接收器实例
# 优先读取 .env / 环境变量中的 EEG_SOURCE 配置，避免把测试脚本锁死在串口模式。
receiver = EEGDataReceiver()

print("\n尝试启动接收器...")
if receiver.start():
    print("✓ 接收器已启动！")
    print("\n实时数据监控（按 Ctrl+C 停止）:")
    print("-" * 70)
    
    try:
        count = 0
        while True:
            latest = receiver.get_latest_data()
            history = receiver.get_history_data(max_points=10)
            
            count += 1
            if count % 10 == 0:  # 每10次循环打印一次
                print(f"\n[{count}] 最新数据:")
                print(f"  数据源: {latest['source']}")
                print(f"  通道: {latest['channel']}")
                print(f"  原始值: {latest['value']:.4f}")
                print(f"  Theta: {latest['theta']:.2f}")
                print(f"  Alpha: {latest['alpha']:.2f}")
                print(f"  Beta:  {latest['beta']:.2f}")
                print(f"  连接状态: {receiver.get_source_status()['connected']}")
                print(f"  缓存数据点: {len(history['values'])}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n停止接收...")
        receiver.stop()
        print("✓ 接收器已停止")
        
else:
    print("✗ 接收器启动失败！")
    print("\n可能的原因:")
    print("  1. EEG_SOURCE 配置错误")
    print("  2. 串口模式下设备不存在或没有权限")
    print("  3. LSL 模式下 pylsl 未安装或采集端尚未开始推流")
    print("\n解决方法:")
    print("  - 串口模式: 检查设备连接和访问权限")
    print("  - LSL 模式: 确认 Windows 采集端已推送同名 LSL 流")

print("\n" + "=" * 70)

