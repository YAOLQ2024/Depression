# EEG Demo 使用说明

更新时间：2026-03-31

这份说明对应当前仓库里已经恢复好的 EEG demo 链路：

```text
Windows 采集端
-> depression/EEG/lsl_sender.py
-> 局域网 LSL 两条流 (EEG_Data / EEG_Features)
-> Linux Flask 端 depression/my_flask_app/flask_app/utils/eeg_receiver.py
-> /eeg/channels + /eeg/classification
-> /eeg-test 和 /SDS 页面
```

## 1. Linux 端配置

当前项目的 Linux 端 `.env` 已经写好了这组 EEG 配置：

```env
EEG_SOURCE=lsl
EEG_LSL_STREAM_NAME=EEG_Data
EEG_LSL_STREAM_TYPE=EEG
EEG_LSL_CHANNEL_MAP=0,1,2
EEG_LSL_FEATURE_STREAM_NAME=EEG_Features
EEG_LSL_FEATURE_STREAM_TYPE=EEG_Features
EEG_LSL_KNOWN_PEERS=10.102.5.24,10.43.18.245
EEG_LSL_SESSION_ID=depression-eeg
EEG_LSL_RESOLVE_SCOPE=machine
EEG_LSL_DISABLE_IPV6=1
```

如果 Windows 采集机 IP 变了，只需要同步改：

1. Linux `.env` 里的 `EEG_LSL_KNOWN_PEERS`
2. Windows 启动命令里的 `--known-peer`

## 2. Windows 采集端准备

Windows 上进入项目目录：

```bash
cd depression/EEG
pip install -r requirements_windows_lsl.txt
```

这里最关键的文件是：

1. `lsl_sender.py`
2. `ble_receiver.py`
3. `eeg_serial.py`

## 3. Windows 启动命令

### 3.1 BLE 模式

如果脑电帽走 BLE，推荐命令：

```bash
python lsl_sender.py --source ble --known-peer 10.102.5.24 --known-peer 10.43.18.245 --session-id depression-eeg --resolve-scope machine --disable-ipv6
```

如果不传 `--address`，脚本会先扫描 BLE 设备，再让你选择。

### 3.2 串口模式

如果采集端走串口，推荐命令：

```bash
python lsl_sender.py --source serial --serial-port COM3 --baud-rate 230400 --known-peer 10.102.5.24 --known-peer 10.43.18.245 --session-id depression-eeg --resolve-scope machine --disable-ipv6
```

### 3.3 无硬件冒烟测试

如果只是想先验证网页链路是否通，可以临时用 mock：

```bash
python lsl_sender.py --source mock --known-peer 10.102.5.24 --known-peer 10.43.18.245 --session-id depression-eeg --resolve-scope machine --disable-ipv6
```

这会推一组模拟三通道波形和模拟特征，便于先确认 UI 和接口。

## 4. Linux Web 端启动

在 Linux 服务器上启动系统：

```bash
cd /home/ZR/data2/Depression/depression
conda activate depression
python3 start_app_gpu.py
```

如果要连同 LLM / RAG 一起跑，则用：

```bash
cd /home/ZR/data2/Depression/depression
./scripts/start_stack.sh
```

Flask 启动后应能看到类似日志：

```text
[EEG] 脑电接收器已启动
  数据源: lsl
  LSL波形流: name=EEG_Data, type=EEG
  LSL特征流: name=EEG_Features, type=EEG_Features
```

如果 Windows 端还没开，会周期性看到：

```text
[EEG][LSL] 等待 EEG原始波形 流: name=EEG_Data, type=EEG
```

## 5. 演示时怎么确认已经接好

### 5.1 先看 Windows 推流端

启动 `lsl_sender.py` 后，应该看到：

```text
[LSL] Raw stream ready:
[LSL] Feature stream ready:
[LSL] Streaming started. Keep this window open.
```

后续会持续打印：

```text
[LSL] wave packets=...
[LSL] feature packets=...
```

### 5.2 再看 Linux 调试页

浏览器打开：

```text
http://<Linux机器IP>:5000/eeg-test
```

正常时会看到：

1. 连接状态变成“已连接”
2. 三个通道波形滚动
3. 分类从 `standby` 慢慢变为 `neutral / positive / negative`

### 5.3 最后看业务页

SDS 页面：

```text
http://<Linux机器IP>:5000/SDS
```

右侧 EEG 面板应开始出现三通道波形。

## 6. 现场排障顺序

如果页面看不到 EEG，按这个顺序查：

1. 先看 Windows `lsl_sender.py` 是否还在持续打印 `wave packets`
2. 再看 Linux Flask 日志是否从“等待流”变成“已连接原始波形流”
3. 再打开 `/eeg-test` 看调试页
4. 最后才去看 `/SDS`

最常见的原因是：

1. Windows 和 Linux 的 `KnownPeers` 没配一致
2. Windows 没带 `--session-id depression-eeg`
3. 两边不在同一局域网
4. Windows 推流端没保持运行

## 7. 当前 demo 能力边界

这次恢复的是“实时接入和显示层”，已经能用于课堂 demo：

1. 三通道波形实时显示
2. EEG 特征流接入
3. 规则版 EEG 分类接口

当前还没有做到：

1. 真实 EEG 落库
2. 真实 EEG 进入综合评分
3. 提交量表时把 EEG 一起写入结果表
