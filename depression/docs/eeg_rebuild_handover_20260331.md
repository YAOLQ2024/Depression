# EEG 当前版本接入实现复现文档

更新时间：2026-03-31

这份文档不是“怎么临时跑起来”的速查表，而是给回退后重新嫁接 EEG 用的还原说明。目标是两件事：

1. 说清楚当前版本 EEG 真正工作的链路到底是什么。
2. 说清楚哪些代码只是旧残留/兼容壳，回退后不要误接。

如果只看一句话总结，当前版本真正稳定在用的 EEG 链路是：

```text
Windows 采集端（BLE 或串口）
-> EEG/lsl_sender.py
-> 局域网 LSL 两条流（EEG_Data / EEG_Features）
-> Linux Flask 端 flask_app/utils/eeg_receiver.py（LSL 模式）
-> /eeg/channels + /eeg/classification
-> 前端页面右侧 EEG 面板（主要是 /journey/screening，也兼容 /SDS）
```

当前版本不是“Linux 直接蓝牙连脑电帽”，也不是“真实 EEG 已经写库并参与综合分”。当前版本做到的是：

1. Windows 端采集并推流。
2. Linux Web 端实时画 3 通道波形。
3. 如果有特征流，则额外做一个规则版 EEG 分类展示。

当前版本还没有做到的是：

1. 把真实 EEG 原始数据/特征写进数据库。
2. 把真实 EEG 参与 `SDS_submit` 或结构化量表提交结果。
3. 把 `scoring_system.py` 里的 `eeg_score` 替换成真实 EEG 分值。

## 1. 当前版本里，哪些文件是这套 EEG 接入的核心

下面这些文件是回退后需要优先保留或迁移的。

| 文件 | 作用 | 回退后是否必须 |
| --- | --- | --- |
| `EEG/lsl_sender.py` | Windows 端把 BLE/串口脑电桥接成 LSL 流 | 必须 |
| `EEG/ble_receiver.py` | Windows 端 BLE 接收器 | 如果采集端走 BLE，则必须 |
| `EEG/eeg_serial.py` | Windows 端串口协议解析器 | 如果采集端走串口，则必须 |
| `EEG/requirements_windows_lsl.txt` | Windows 采集端最小依赖 | 建议保留 |
| `depression/.env` | 当前实际运行的 EEG 配置 | 必须参考 |
| `depression/.env.example` | EEG 配置模板 | 建议保留 |
| `depression/my_flask_app/flask_app/__init__.py` | 启动时加载 `.env` | 必须确认旧版也有 |
| `depression/my_flask_app/app.py` | Flask 启动时预热 EEG 接收器 | 建议保留 |
| `depression/my_flask_app/flask_app/utils/eeg_receiver.py` | Linux 端统一 EEG 接收服务 | 必须 |
| `depression/my_flask_app/flask_app/views/test.py` | `/eeg/*` 接口定义 | 必须迁移接口段 |
| `depression/my_flask_app/flask_app/templates/journey/screening.html` | 当前更完整的 EEG 展示面板 | 推荐 |
| `depression/my_flask_app/flask_app/templates/SDS_working2.html` | 旧 SDS 页上的 EEG 波形展示 | 可选 |
| `depression/my_flask_app/flask_app/templates/eeg_test.html` | 调试页 | 强烈建议保留 |
| `depression/my_flask_app/test_eeg.py` | CLI 烟雾测试脚本 | 建议保留 |

另外，`depression/docs/eeg_windows_lsl_setup.md` 是一份偏“操作说明”的文档，这份新文档比它更偏“工程复现说明”。

## 2. 当前实际运行配置

当前运行环境中的 EEG 相关 `.env` 配置是：

来源：`depression/.env:54-64`

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

这说明当前版本实际不是串口直连，而是：

1. Linux 端明确跑 `lsl` 模式。
2. 已启用特征流，所以分类接口理论上应该可用。
3. 已使用 `KnownPeers + SessionID + machine + IPv6 disable` 的固定联调模式，而不是纯组播发现。

`depression/.env.example:40-80` 里也已经补了完整模板，回退后如果旧版没有这些变量，直接把这一段搬过去。

## 3. 启动链路是怎么串起来的

### 3.1 `.env` 是谁加载的

`depression/my_flask_app/flask_app/__init__.py:8-16` 会在创建 Flask app 前加载项目根目录的 `.env`：

1. 先把项目根目录加入 `sys.path`。
2. 再执行 `load_dotenv(project_root / '.env', override=True)`。

这一步很关键。因为 `eeg_receiver.py` 的行为几乎全靠环境变量驱动。如果回退后的版本没有这段，那么 EEG 会退回默认值，通常就会：

1. 误用 `serial` 模式。
2. 找不到 LSL 流。
3. 不会启用 `KnownPeers` 和 `SessionID`。

### 3.2 Flask 服务启动时，谁先把 EEG 接收器拉起来

`depression/my_flask_app/app.py:12-28` 在 `create_app()` 之前先做了一次：

```python
from flask_app.utils.eeg_receiver import get_eeg_receiver
eeg_receiver = get_eeg_receiver()
```

作用是：

1. Flask 一启动就尝试连接 EEG。
2. 启动后 1 秒打印一次初始统计。
3. 如果设备未连，也不会阻断整个服务，只会打印警告。

这不是唯一入口。因为后面每个 `/eeg/*` 路由里也都会调用 `get_eeg_receiver()`，所以即便启动时没连上，后续访问接口时它也会尝试重建。

### 3.3 单例和自动重启机制

`depression/my_flask_app/flask_app/utils/eeg_receiver.py:971-1016` 定义了全局单例 `eeg_receiver` 和 `get_eeg_receiver()`。

`_receiver_needs_restart()` 会在以下情况返回 `True`：

1. 还没有实例。
2. `receiver.running` 为假。
3. 原始波形线程死掉。
4. 情绪推理线程死掉。
5. LSL 特征线程本来应该有，但已经死掉或根本没起来。
6. 出现 `liblsl`/`pylsl` 相关错误且主线程已不活跃。

所以这套实现不是“一次启动一次用到底”，而是“按接口访问时可自恢复”。

## 4. Windows 采集端到底做了什么

### 4.1 真实入口是 `EEG/lsl_sender.py`

`EEG/lsl_sender.py:1-208` 是当前版本 Windows 采集端的关键桥接器。

它支持两种输入源：

1. `--source ble`
2. `--source serial`

但不管底层来源是什么，输出给 Linux 的统一都是 LSL。

### 4.2 Windows 端发出的两条 LSL 流

#### 原始波形流

定义位置：`EEG/lsl_sender.py:102-110`

流信息：

1. `name=EEG_Data`
2. `type=EEG`
3. 通道数 = 3
4. 采样率默认 `500Hz`
5. 数据类型 = `float32`

它每次 push 一个 3 维 sample：

```python
[packet.ch[0], packet.ch[1], packet.ch[2]]
```

发送端给这 3 个通道写的 metadata label 是：

1. `F3`
2. `F4`
3. `Fz`

定义位置：`EEG/lsl_sender.py:105-109`

#### 特征流

定义位置：`EEG/lsl_sender.py:113-125`

流信息：

1. `name=EEG_Features`
2. `type=EEG_Features`
3. 通道数 = 10
4. 发送频率 nominal = `1.0Hz`
5. 数据类型 = `float32`

特征顺序固定为：

1. `FAA`
2. `theta_ch0`
3. `alpha_ch0`
4. `beta_ch0`
5. `theta_ch1`
6. `alpha_ch1`
7. `beta_ch1`
8. `theta_ch2`
9. `alpha_ch2`
10. `beta_ch2`

真正 push 的 sample 在 `EEG/lsl_sender.py:158-179`，写死就是上面这 10 个值。

### 4.3 Windows 端 BLE/串口底层协议

#### BLE 模式

`EEG/ble_receiver.py:29-225`

关键点：

1. 通过 `bleak` 连 BLE 设备。
2. 订阅 NUS TX characteristic：`6e400003-b5a3-f393-e0a9-e50e24dcca9e`
3. 收到通知后自己拼帧、校验 CRC、解析波形包和特征包。

#### 串口模式

`EEG/eeg_serial.py:154-220`

当前串口协议定义是：

1. 波形包总长 `19` 字节。
2. 特征包总长 `77` 字节。
3. 波形包结构：

```text
[06][09][01][seq:2B][3个float:12B][CRC16:2B]
```

4. 特征包结构：

```text
[06][09][02][18个float:72B][CRC16:2B]
```

这个协议定义非常重要，因为它和 Flask 端 `eeg_receiver.py` 里的 `serial` 解析不是同一版，后面会单独说。

### 4.4 当前 Windows 端推荐启动命令

由于当前 Linux `.env` 已经写死：

1. `EEG_LSL_KNOWN_PEERS=10.102.5.24,10.43.18.245`
2. `EEG_LSL_SESSION_ID=depression-eeg`
3. `EEG_LSL_RESOLVE_SCOPE=machine`
4. `EEG_LSL_DISABLE_IPV6=1`

所以 Windows 侧要和它对齐，推荐命令是：

```bash
python lsl_sender.py --source ble --known-peer 10.102.5.24 --known-peer 10.43.18.245 --session-id depression-eeg --resolve-scope machine --disable-ipv6
```

如果 Windows 机器换了 IP，只改 `--known-peer` 和 Linux `.env` 的 `EEG_LSL_KNOWN_PEERS`，其他不动。

### 4.5 为什么现在推荐 LSL，而不是 Linux 直连设备

原因有两层：

1. Windows 端 BLE 依赖里有 WinRT，只适合采集端，不适合 Linux 服务器继续直连。
2. 当前 Web 端真正稳定打通的是 LSL 模式，串口直连那套在 Flask 里有旧协议残留，风险更大。

## 5. Linux Web 端接收器是怎么工作的

### 5.1 接收器总入口

`depression/my_flask_app/flask_app/utils/eeg_receiver.py:138-1016`

`EEGDataReceiver` 同时支持两种来源：

1. `serial`
2. `lsl`

但当前 `.env` 明确是 `lsl`。

### 5.2 环境变量怎么决定行为

`eeg_receiver.py:152-176`

主要读取这些变量：

1. `EEG_SOURCE`
2. `EEG_SERIAL_PORT`
3. `EEG_BAUD_RATE`
4. `EEG_LSL_STREAM_NAME`
5. `EEG_LSL_STREAM_TYPE`
6. `EEG_LSL_CHANNEL_MAP`
7. `EEG_LSL_FEATURE_STREAM_NAME`
8. `EEG_LSL_FEATURE_STREAM_TYPE`
9. `EEG_LSL_RESOLVE_TIMEOUT`
10. `EEG_LSL_PULL_TIMEOUT`

其中 `EEG_LSL_CHANNEL_MAP` 是关键，它决定 LSL sample 的第几个索引映射到 `channel1~3`。

当前值是：

```env
EEG_LSL_CHANNEL_MAP=0,1,2
```

所以：

1. `channel1 <- sample[0]`
2. `channel2 <- sample[1]`
3. `channel3 <- sample[2]`

### 5.3 LSL 运行时配置是自动生成的

`eeg_receiver.py:79-135`

如果环境里配置了：

1. `EEG_LSL_KNOWN_PEERS`
2. `EEG_LSL_SESSION_ID`
3. `EEG_LSL_RESOLVE_SCOPE`
4. `EEG_LSL_DISABLE_IPV6`

接收器会在临时目录生成一个 `depression_lsl_receiver.cfg`，然后把路径塞给 `LSLAPICFG`。

这意味着回退后如果你保留这段逻辑，就不需要手写 `lsl_api.cfg`。

### 5.4 接收器启动时会拉起哪些线程

`eeg_receiver.py:300-347`

当前 LSL 模式下会拉起 3 条线程：

1. 原始波形线程 `EEG-LSL-Wave`
2. 特征线程 `EEG-LSL-Feature`
3. 规则分类线程 `EEG-Emotion-Inference`

其中：

1. 原始波形线程负责消费 `EEG_Data`
2. 特征线程负责消费 `EEG_Features`
3. 分类线程每 1 秒基于最近窗口重新计算一次结果

### 5.5 原始波形缓存结构

`eeg_receiver.py:187-193`

每个通道保留：

1. `values: deque(maxlen=2000)`
2. `timestamps: deque(maxlen=2000)`

也就是按注释的设计，大约保留最近 4 秒的波形数据，默认按 500Hz 估算。

### 5.6 特征缓存结构

`eeg_receiver.py:194-223`

每个通道保留：

1. `current`
2. `history.theta`
3. `history.alpha`
4. `history.beta`
5. `history.timestamps`

`history` 的长度是 `100`，足够给当前规则分类使用。

### 5.7 原始波形流怎么接收

`eeg_receiver.py:540-620`

流程是：

1. 用 `resolve_byprop(name=...)` 找流。
2. 如果按 `name` 找不到，再按 `type` 找。
3. 找到后创建 `StreamInlet(..., max_buflen=2, recover=True)`。
4. 每次 `pull_sample(timeout=self.lsl_pull_timeout)`。
5. 按 `EEG_LSL_CHANNEL_MAP` 把 sample 的 3 个索引映射到 `channel1~3`。
6. 调用 `_append_wave_sample()` 写入缓存。

### 5.8 特征流怎么接收

`eeg_receiver.py:577-647`

特征流支持两种输入格式：

1. 9 维：`[theta, alpha, beta] * 3`
2. 10 维：`[FAA + 9维特征]`

如果是 10 维，接收器只用 `FAA` 来判断偏移量，后面真正写入缓存的依然只是三组：

1. `theta`
2. `alpha`
3. `beta`

也就是说：

1. `FAA` 目前不会被单独缓存到 `features_data`。
2. 当前分类逻辑也不直接吃发送端的 `FAA`，而是自己从左右 `alpha` 做 `log(alpha_left) - log(alpha_right)`。

### 5.9 分类逻辑到底怎么算

`eeg_receiver.py:792-947`

当前分类是一个规则版推理，不是模型。

窗口和阈值：

1. 窗口 `WINDOW_SEC = 4.0`
2. `T_ASYM = 0.1`
3. `T_BT_POS = 0.7`
4. `T_BT_NEG = 0.3`
5. `MIN_SCORE = 0.2`
6. `MIN_DATA_POINTS = 3`

使用的输入只有左右两个通道，也就是：

1. `channel1` 视为 left
2. `channel2` 视为 right

`channel3` 只用于画图，不参与分类。

分类结果可能是：

1. `standby`
2. `positive`
3. `negative`
4. `neutral`

`reason` 可能是：

1. `initializing`
2. `insufficient_data`
3. `invalid_feature`
4. `ok`

## 6. 后端暴露给前端的 EEG 接口

接口都在 `depression/my_flask_app/flask_app/views/test.py:463-596`。

### 6.1 `/eeg/channels`

这是业务页面真正最核心的接口。

实现：`test.py:489-512`

返回结构来自 `eeg_receiver.py:696-742`，核心形状如下：

```json
{
  "success": true,
  "data": {
    "channel1": {
      "waveform": [...],
      "timestamps": [...],
      "features": {
        "current": {"theta": 0.0, "alpha": 0.0, "beta": 0.0, "timestamp": 0},
        "history": {"theta": [...], "alpha": [...], "beta": [...], "timestamps": [...]}
      }
    },
    "channel2": {},
    "channel3": {},
    "stats": {
      "total_packets": 0,
      "data_packets": 0,
      "feature_packets": 0,
      "invalid_packets": 0
    },
    "source": {
      "source_mode": "lsl",
      "connected": true,
      "last_error": "",
      "last_data_timestamp": 0.0
    }
  }
}
```

前端拿到后一般只取：

1. `channel1.waveform`
2. `channel2.waveform`
3. `channel3.waveform`
4. `source.connected`
5. `source.last_error`

### 6.2 `/eeg/classification`

实现：`test.py:514-530`

直接返回 `receiver.get_emotion_classification(window_sec=4.0)`。

典型结构：

```json
{
  "success": true,
  "data": {
    "label": "neutral",
    "score": 0.5,
    "window_sec": 4.0,
    "timestamp": 1710000000.0,
    "features": {
      "alpha_left": 0.0,
      "alpha_right": 0.0,
      "beta_left": 0.0,
      "beta_right": 0.0,
      "theta_left": 0.0,
      "theta_right": 0.0,
      "alpha_log_left": 0.0,
      "alpha_log_right": 0.0,
      "fai": 0.0,
      "beta_theta_left": 0.0,
      "beta_theta_right": 0.0
    },
    "reason": "ok"
  }
}
```

### 6.3 其他接口的定位

#### `/eeg/latest`

`test.py:463-487`

只适合调试，不是主要业务接口。

#### `/eeg/history`

`test.py:532-553`

兼容旧前端的历史波形接口。

#### `/eeg/stream`

`test.py:560-596`

SSE 接口，当前更多给调试页用，不是业务页面主通路。

#### `/eeg-test`

`test.py:555-558`

返回专门的调试页面，强烈建议在回退后也保留。

## 7. 前端现在是怎么消费 EEG 的

### 7.1 当前更完整的一版：`/journey/screening`

模板位置：`depression/my_flask_app/flask_app/templates/journey/screening.html:219-510`

这一页的 EEG 面板能力最完整，包含：

1. 三个 canvas 波形图。
2. 连接状态 badge。
3. 自动刻度文字。
4. 分类结果文本。
5. source 错误/等待提示。

前端轮询频率是：

1. `/eeg/channels` 每 `150ms` 一次，见 `screening.html:463-485` 和 `screening.html:508`
2. `/eeg/classification` 每 `1200ms` 一次，见 `screening.html:487-500` 和 `screening.html:509`

这一页的波形绘制特点：

1. 前端只截最近 `200` 个点。
2. 自动算 baseline 和 amplitude。
3. 会根据实时幅值自动缩放。

这版页面是回退后最推荐复用的 EEG UI。

### 7.2 旧 SDS 页：`/SDS`

模板位置：`depression/my_flask_app/flask_app/templates/SDS_working2.html:395-892`

这页也有 EEG 面板，但比 `journey/screening` 简陋很多：

1. 只画 3 个通道波形。
2. 只请求 `/eeg/channels`。
3. 不请求 `/eeg/classification`。
4. 不显示真实连接状态和错误信息。
5. 前端归一化是写死按 `[-100, 100]` 范围缩放，不如 `journey/screening` 的自动缩放稳。

轮询频率是：

1. `/eeg/channels` 每 `100ms` 一次，见 `SDS_working2.html:816-838`

所以如果回退后只需要“页面上能看到 EEG 波形”，搬这版也够用；但如果要保留当前版本完整体验，建议优先搬 `journey/screening` 的 EEG 面板逻辑。

### 7.3 一个容易忽略的点：`capture_eeg` 不等于真正开启轮询

`depression/new_features/care_flow/service.py:88-96` 里默认设置是：

```python
"capture_eeg": False
```

`journey/screening.html:203-215` 那块“EEG 采集已启用/未启用”只是 UI 文案和样式提示。

真正的 JS 轮询逻辑在 `screening.html:352-510`，并没有被 `capture_eeg` 条件包住，也就是说：

1. 就算设置显示“未启用”，页面仍然会拉 `/eeg/channels` 和 `/eeg/classification`。
2. 这个设置目前更像一个产品态配置，不是技术层开关。

## 8. 当前版本里，EEG 到了哪里，没到哪里

这部分必须看清，否则回退时很容易以为“当前版本已经把 EEG 打通到结果页和数据库了”。

### 8.1 当前版本已经打通的部分

1. Windows 采集端到 Linux Web 端的实时链路。
2. Web 页面右侧 EEG 波形显示。
3. 基于特征流的规则分类接口。
4. 调试页和 CLI 脚本的连通性验证。

### 8.2 当前版本没有打通的部分

#### `SDS_submit` 不接收 EEG

`depression/my_flask_app/flask_app/views/test.py:61-128`

`/SDS/submit` 只收：

1. `answers`
2. `totalTime`

它不会收：

1. EEG 分类结果
2. EEG 原始数据
3. EEG 特征

#### `SDS_submit_with_emotion` 也没有真实 EEG

`test.py:634-778`

这个接口名字看起来像“多模态综合提交流程”，但它实际只处理：

1. `answers`
2. `totalTime`
3. `emotionData`

没有读取真实 EEG 接口结果。

#### `scoring_system.py` 里的 `eeg_score` 是模拟值

`depression/my_flask_app/utils/scoring_system.py:262-347`

这里有个特别关键的事实：

1. `calculate_comprehensive_score()` 虽然带了 `eeg_data` 参数。
2. 但内部实际调用的是 `calculate_eeg_score(emotion_score=emotion_score)`。
3. `calculate_eeg_score()` 明确写着“当前使用视觉情感 AI 分数作为模拟数据”。

也就是：

1. 当前综合评分里的 `eeg_score` 不是来自真实 EEG。
2. 它只是把 emotion score 再复用一次。

#### `journey/screening` 也不落 EEG

`journey/screening` 只是在页面上显示 EEG 辅助面板，并没有把 EEG 随量表表单一起提交到后端。

结论：

当前版本的 EEG 是“实时辅助显示层”，不是“结果持久化层”。

## 9. 当前代码里必须记住的几个坑

### 9.1 Flask 里的 `serial` 解析是旧协议，不要当成当前真实链路

这是最重要的坑。

`depression/my_flask_app/flask_app/utils/eeg_receiver.py:447-507` 里的 `serial` 模式认为：

1. 波形包长度是 `10`
2. 特征包长度是 `18`
3. 波形包格式是 `[06][09][type][channel][float][crc]`

但 `EEG/eeg_serial.py:4-7, 154-220` 里的当前协议明确定义为：

1. 波形包长度 `19`
2. 特征包长度 `77`
3. 波形包里有 `seq` 和 3 个 float
4. 特征包里有 18 个 float

这两者不是同一个协议。

所以结论很明确：

1. 当前版本真正可工作的链路是 LSL。
2. Flask 里的 `serial` 分支是旧残留，不应作为回退后复现的基线。

如果回退后你想保留“当前版本行为”，优先复现 LSL 链路，不要走 Flask 直连串口。

### 9.2 前端通道标签和发送端 metadata 标签并不一致

发送端 `lsl_sender.py:105-109` 写的是：

1. `F3`
2. `F4`
3. `Fz`

但前端页面上显示的是：

1. `F3`
2. `F4`
3. `Fz`

对应位置：

1. `SDS_working2.html:407-420`
2. `journey/screening.html:231-238`

这说明当前页面上的标签更偏 UI 展示，并没有严格绑定 LSL metadata。

回退后有两个选择：

1. 完全按当前行为复刻，继续显示旧标签
2. 顺手修正为和发送端一致的 `F3 / F4 / Fz`

但一定要在改动时明确说明，不然很容易发生“代码接对了，但标签解释错了”。

### 9.3 分类只用左右两个通道

`eeg_receiver.py:801-839`

当前分类只取：

1. `channel1` 的 alpha/beta/theta
2. `channel2` 的 alpha/beta/theta

`channel3` 不参与分类。

所以如果回退后发现三通道都在画，但分类不稳定，优先检查的是左/右两个通道的特征流，不是中间通道。

### 9.4 没有特征流时，波形能画，但分类会长期 `standby`

这不是 bug，是当前设计。

原因：

1. 原始波形接口和分类接口分离。
2. 分类依赖特征流里的 theta/alpha/beta。
3. 只推 `EEG_Data` 不推 `EEG_Features` 时，`/eeg/channels` 还能正常显示波形，但 `/eeg/classification` 很可能一直是 `standby`。

### 9.5 `depression_knn.py` / `model.pkl` / `live_dashboard.py` 不是 Web 链路的一部分

仓库根目录 `EEG/` 下还有：

1. `depression_knn.py`
2. `model.pkl`
3. `live_dashboard.py`

这些更偏独立实验/桌面分类流程。当前 Web 接入链路里并没有调用它们。

所以回退后如果目标只是复原“现在网页上的 EEG 接法”，这些不是必搬项。

## 10. 回退后最小可复现方案

如果你回退到上一版，只想尽快把“当前 EEG 接入方式”恢复出来，建议按下面的最小闭环做。

### 10.1 Windows 端必须保留

把这 4 个文件保留到采集端环境：

1. `EEG/lsl_sender.py`
2. `EEG/ble_receiver.py`
3. `EEG/eeg_serial.py`
4. `EEG/requirements_windows_lsl.txt`

### 10.2 Linux 端必须保留

至少迁移这些内容：

1. `depression/.env` 里的 EEG 配置段
2. `depression/my_flask_app/flask_app/__init__.py` 的 `.env` 加载逻辑
3. `depression/my_flask_app/flask_app/utils/eeg_receiver.py`
4. `depression/my_flask_app/app.py` 里预热 `get_eeg_receiver()` 的逻辑
5. `depression/my_flask_app/flask_app/views/test.py` 里的 `/eeg/channels` 和 `/eeg/classification`

如果旧版没有依赖，也要补：

1. `pylsl`
2. `pyserial`

### 10.3 最低可验证页面

优先保留 `depression/my_flask_app/flask_app/templates/eeg_test.html`。

原因是：

1. 它适合先验证后端 EEG 接口本身是否通。
2. 比直接进复杂业务页面更容易排错。

### 10.4 推荐最终业务页面

如果旧版没有 `journey/` 页面，最简单是把 EEG 面板 graft 到你回退后的主问卷页。

如果能保留当前体验，优先级建议是：

1. 优先复用 `journey/screening.html` 的 EEG 面板逻辑
2. 其次复用 `SDS_working2.html` 的 EEG 波形逻辑

## 11. 回退后完整嫁接步骤

### 步骤 1：先恢复 Linux 接收层

先不要急着接页面。

先做：

1. 恢复 `.env` 的 EEG 配置。
2. 恢复 `eeg_receiver.py`。
3. 恢复 `app.py` 里的启动预热。
4. 恢复 `/eeg/channels` 和 `/eeg/classification`。

做到这一步后，只要 Windows 端在推流，Linux 端理论上就已经具备接收能力。

### 步骤 2：先用 CLI 或调试页验通

先用：

```bash
python depression/my_flask_app/test_eeg.py
```

或者打开：

```text
/eeg-test
```

先确认：

1. `/eeg/channels` 能返回三通道波形。
2. `source.connected=true`。
3. 如果特征流在推，`/eeg/classification` 的 `reason` 会从 `initializing/insufficient_data` 变成 `ok`。

### 步骤 3：再把前端 EEG 面板 graft 到业务页

要搬的不是整页，而是这几部分：

1. 三个 canvas 容器
2. 拉 `/eeg/channels` 的 JS
3. 波形绘制函数
4. 如果要完整体验，再加 `/eeg/classification`、连接 badge、source note

### 步骤 4：最后再决定要不要把 EEG 真正写库

如果你的目标只是“回退后保留当前 EEG 接入能力”，到上一步已经够了。

如果你的目标是“让 EEG 真正进入业务结果”，还需要额外做一层当前版本并没有完成的工作：

1. 设计 EEG 落库字段
2. 在提交表单时把 EEG 摘要一并提交
3. 把 `scoring_system.py` 中模拟的 `eeg_score` 换成真实 EEG 结果

这三件事不属于当前版本已完成内容，不要误以为现在已经有。

## 12. 回退后验证 checklist

### Windows 采集端

应看到类似日志：

```text
[LSL] Raw stream ready:
[LSL] Feature stream ready:
[LSL] Streaming started. Keep this window open.
```

并持续看到：

```text
[LSL] wave packets=500 ...
```

如果开了特征流，还应看到：

```text
[LSL] feature packets=...
```

### Linux Flask 启动时

应看到类似日志：

```text
[EEG] 脑电接收器已启动
数据源: lsl
LSL波形流: name=EEG_Data, type=EEG
LSL特征流: name=EEG_Features, type=EEG_Features
LSL通道映射: [0, 1, 2]
```

如果还没连上 Windows，则会周期性打印：

```text
[EEG][LSL] 等待 EEG原始波形 流: name=EEG_Data, type=EEG
```

### 浏览器调试页 `/eeg-test`

应看到：

1. 状态从等待变为 connected。
2. 波形图开始滚动。
3. 最新数据区持续刷新。

### 业务页 `/journey/screening`

应看到：

1. 右侧 EEG badge 从 `Waiting` 变为 `Stable`
2. `eegSourceNote` 从等待提示变成“EEG 原始波形已接入前端监测面板。”
3. 如果特征流正常，`eegLabel` 不再长期停在“尚未收到 EEG 分类结果”

## 13. 如果我之后接手回退版本，我会怎么复原

如果你回退后让我照着这份文档复原，我会按下面顺序做：

1. 先检查旧版是否还能在 `flask_app/__init__.py` 里加载 `.env`
2. 把 `eeg_receiver.py` 整体迁进去
3. 把 `app.py` 的 EEG 预热段迁进去
4. 把 `/eeg/channels`、`/eeg/classification`、`/eeg-test` 路由迁进去
5. 把 `.env` 的 EEG 配置段补齐
6. 用 `test_eeg.py` 或 `/eeg-test` 验通
7. 再把 `journey/screening` 或目标页的 EEG 面板 graft 上去
8. 最后才评估要不要做真正的 EEG 落库和综合评分接入

这样做能保证我们先复原“当前版本已经真实跑通的部分”，而不是一上来就陷入旧串口协议、旧综合评分或者假闭环代码里。

## 14. 结论

回退后要复原当前版本 EEG，最重要的不是“把所有带 EEG 字样的文件都搬过去”，而是只保留当前真正工作的主链：

1. Windows `lsl_sender.py`
2. Linux `.env` LSL 配置
3. Flask `eeg_receiver.py`
4. `/eeg/channels` 和 `/eeg/classification`
5. 一个能展示三通道波形的前端面板

只要这 5 块在，当前版本的 EEG 连接能力就能复现。

最需要避免的是两件事：

1. 误把 Flask 里的旧 `serial` 解析当成当前生产链。
2. 误以为当前版本已经把真实 EEG 落库并接入综合评分。

这两件事如果不先澄清，回退后的嫁接会很容易走偏。
