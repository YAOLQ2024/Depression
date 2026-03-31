# Windows EEG -> Linux Web 实时接入说明

这套项目现在推荐用 `LSL (Lab Streaming Layer)` 连接 EEG。

原则很简单：

1. Windows 电脑继续负责蓝牙或串口连脑电帽。
2. Windows 把实时波形和特征推成 LSL 流。
3. Linux 上的 `depression` 项目只负责接收 LSL，并在网页里画图。

这样做的原因是 Windows 端原来的蓝牙链路已经是可用的，而 Linux 不适合继续复用那套 WinRT 蓝牙依赖。

## 需要放到 Windows 电脑上的文件

把下面这些文件放到同一个目录中，保持相对导入不变：

- `EEG/ble_receiver.py`
- `EEG/eeg_serial.py`
- `EEG/lsl_sender.py`
- `EEG/requirements_windows_lsl.txt`

如果同事的 Windows 环境里已经能运行原来的 EEG 项目，也可以只额外拷贝 `EEG/lsl_sender.py`。

## Windows 环境安装

建议使用 Python 3.10 或 3.11。

### 1. 创建虚拟环境

```bash
cd path\to\EEG
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

### 2. 安装最小依赖

```bash
pip install -r requirements_windows_lsl.txt
```

如果同事原来已经装过完整的 `EEG/requirements.txt`，这一步通常可以跳过。

## Windows 端运行方式

### 方式 A：蓝牙脑电帽

```bash
cd path\to\EEG
.venv\Scripts\activate
python lsl_sender.py --source ble
```

运行后会扫描蓝牙设备，终端里输入编号即可连接。

如果你已经知道设备地址，也可以直接指定：

```bash
python lsl_sender.py --source ble --address AA:BB:CC:DD:EE:FF
```

### 方式 B：串口设备

```bash
python lsl_sender.py --source serial --port COM5
```

如果波特率不是默认值 `230400`，要显式传入：

```bash
python lsl_sender.py --source serial --port COM5 --baudrate 115200
```

## Windows 端会发出什么流

默认会发两条 LSL 流：

1. 波形流
   - `name=EEG_Data`
   - `type=EEG`
   - 3 通道原始波形，顺序是 `F3 / F4 / Fpz`

2. 特征流
   - `name=EEG_Features`
   - `type=EEG_Features`
   - 10 维，顺序是：
   - `FAA`
   - `theta_ch0, alpha_ch0, beta_ch0`
   - `theta_ch1, alpha_ch1, beta_ch1`
   - `theta_ch2, alpha_ch2, beta_ch2`

如果你只想先推波形，不推特征，可以这样运行：

```bash
python lsl_sender.py --source ble --disable-feature-stream
```

这样网页里的波形仍然能显示，但 EEG 分类接口会更可能显示 `standby`。

## Linux 服务器这边怎么接

### 1. 安装依赖

在 Linux 的 `depression` 项目环境中安装：

```bash
pip install pylsl pyserial
```

或者按项目现有 requirements 安装。

### 2. 配置 `.env`

参考 [`.env.example`](/home/ZR/data2/Depression/depression/.env.example#L39)，至少需要：

```env
EEG_SOURCE=lsl
EEG_LSL_STREAM_NAME=EEG_Data
EEG_LSL_STREAM_TYPE=EEG
EEG_LSL_CHANNEL_MAP=0,1,2
EEG_LSL_FEATURE_STREAM_NAME=EEG_Features
EEG_LSL_FEATURE_STREAM_TYPE=EEG_Features
```

如果 Windows 端没有开特征流，就把最后两行删掉或注释掉。

### 3. 启动 Web 项目

启动 `depression/my_flask_app/app.py` 对应的 Flask 服务。

现在新的任务流页面会在结构化问诊页显示 EEG 辅助面板：

- `/journey/screening`

这个页面会轮询：

- `/eeg/channels`
- `/eeg/classification`

## 当前网页里 EEG 放在哪里

EEG 不再作为一个独立桌面弹窗，而是作为问诊页右侧的“辅助脑电面板”存在。

设计取舍是：

1. 主链还是 `建档 -> 虚拟医生 -> 量表问诊 -> 风险分层 -> 调控决策 -> 执行 -> 历史`
2. EEG 是辅助层，不阻断主链
3. 即便 EEG 没接上，量表问诊和整个闭环仍然能继续

## 你需要让同事知道的运行顺序

每次联调都按这个顺序走：

1. Windows 电脑和 Linux 服务器连到同一个局域网
2. Windows 上激活 EEG 虚拟环境
3. Windows 上运行 `python lsl_sender.py --source ble`
4. 确认终端里看到 LSL 已开始推流
5. Linux 上启动 Flask 项目
6. 浏览器打开 `/journey/screening`
7. 看右侧 EEG 面板是否从“等待连接”变成“已连接”

## 常见问题

### 页面一直显示“等待连接”

优先检查：

1. Windows 和 Linux 是否在同一个局域网
2. Windows 端 `lsl_sender.py` 是否真的在运行
3. `.env` 里的 `EEG_LSL_STREAM_NAME` / `EEG_LSL_FEATURE_STREAM_NAME` 是否和 Windows 端一致
4. Linux 环境里是否成功安装了 `pylsl`

如果 Windows 端已经出现：

```text
[LSL] Streaming started. Keep this window open.
[LSL] wave packets=500 ...
```

但 Linux 端仍然一直打印：

```text
[EEG][LSL] 等待 EEG原始波形 流: name=EEG_Data, type=EEG
```

那通常不是代码坏了，而是 LSL 的组播发现被网络/VPN/防火墙挡住了。此时建议直接改成 `KnownPeers` 模式。

#### 方案：绕过组播发现，直接指定双方 IP

先分别查两台机器的局域网 IP：

1. Linux：

```bash
hostname -I
```

2. Windows：

```powershell
ipconfig
```

找到正在联网的那张网卡的 `IPv4 Address`。

假设：

- Linux = `10.102.5.24`
- Windows = `10.102.5.33`

那么：

1. Linux 的 `.env` 里增加：

```env
EEG_LSL_KNOWN_PEERS=10.102.5.24,10.102.5.33
EEG_LSL_SESSION_ID=depression-eeg
EEG_LSL_RESOLVE_SCOPE=machine
EEG_LSL_DISABLE_IPV6=1
```

2. Windows 端改成这样启动：

```bash
python lsl_sender.py --source ble --known-peer 10.102.5.24 --known-peer 10.102.5.33 --session-id depression-eeg --resolve-scope machine --disable-ipv6
```

`lsl_sender.py` 现在会自动生成 `lsl_api.cfg`，不需要你手写配置文件。

3. 然后先启动 Windows 推流，再启动 Linux Flask。

这个模式的好处是：

1. 不依赖校园网/公司网的组播设置
2. 不容易被 Docker / Tailscale / VPN 虚拟网卡干扰
3. 更适合你们这种一台 Windows 采集、一台 Linux 展示的固定联调

### 波形有了，但分类一直是 `standby`

这通常说明：

1. 只推了波形，没有推特征流
2. 特征流名字或类型不匹配
3. 特征流格式不是 `[FAA + theta/alpha/beta * 3]` 或 `[theta/alpha/beta * 3]`

### Linux 上装不了 WinRT 包

这是正常现象。WinRT 依赖只应该安装在 Windows 采集端，不应该装在 Linux 服务器上。

## 现在这套接法的工程边界

当前已经可以稳定支持：

1. Windows 采集
2. Linux 网页实时画 3 通道 EEG 波形
3. 在有特征流时做基础 EEG 分类辅助显示

当前还没有实现的是：

1. 更复杂的调控引擎
2. 数字人实时驱动
3. EEG 直接参与调控决策的闭环控制

这些后续都可以在不推翻现有网页结构的前提下继续往里接。
