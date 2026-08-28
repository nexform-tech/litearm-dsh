# litearm-dsh

DeepSeek Harness 驱动的 LiteArm 机械臂控制 — 用自然语言控制真实机械臂。

```
你: "回到零位，然后画一个边长为 10cm 的正方形"
LLM: 规划 → get_arm_state → move_home → compute_ik×4 → move_linear×4 → 完成 ✅
```

## 目录

- [架构](#架构)
- [安装](#安装)
- [快速开始](#快速开始)
- [使用方式](#使用方式)
  - [CLI 交互模式](#cli-交互模式)
  - [单次命令模式](#单次命令模式)
  - [Python API](#python-api)
- [工具参考](#工具参考)
  - [运动控制](#运动控制)
  - [状态查询](#状态查询)
  - [末端操作](#末端操作)
  - [轨迹](#轨迹)
  - [配置](#配置)
  - [安全](#安全)
- [安全架构](#安全架构)
- [配置](#配置-1)
- [常见问题](#常见问题)
- [开发](#开发)

## 架构

```
┌──────────────────────────────────────────────────┐
│ DeepSeek API (deepseek-chat / deepseek-reasoner) │
│ LLM 推理 + 工具选择                                │
└──────────────────────┬───────────────────────────┘
                       │ HTTPS
┌──────────────────────┴───────────────────────────┐
│ litearm-dsh (Python)                              │
│                                                   │
│  ┌───────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ agent.py  │  │   tools/     │  │ safety_gate │ │
│  │ Harness/  │──│ 6 组 42 工具  │──│ 参数校验     │ │
│  │ OpenAI    │  │              │  │ 高危警告     │ │
│  └───────────┘  └──────────────┘  └─────┬──────┘ │
│                                         │         │
│                              ┌──────────┴──────┐  │
│                              │ arm_handle.py   │  │
│                              │ Arm 连接单例      │  │
│                              └──────────┬──────┘  │
└─────────────────────────────────────────┼─────────┘
                                          │ zenoh
┌─────────────────────────────────────────┴─────────┐
│ litearm-server                                     │
│ watchdog · 斜率限制 · 关节限位 · 碰撞检测             │
└─────────────────────────────────────────┬─────────┘
                                          │ CAN
┌─────────────────────────────────────────┴─────────┐
│ LiteArm 7-DOF 机械臂                               │
└───────────────────────────────────────────────────┘
```

### 模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| Agent 入口 | `agent.py` | DeepSeek Harness SDK / OpenAI tool calling 双路径 |
| 安全网关 | `safety_gate.py` | 30+ 参数校验方法，统一拦截所有工具调用 |
| 连接管理 | `arm_handle.py` | litearm.Arm 单例，线程安全 |
| 运动控制 | `tools/move.py` | 10 个运动工具 |
| 状态查询 | `tools/query.py` | 6 个查询工具 |
| 末端操作 | `tools/operate.py` | 4 个操作工具 |
| 轨迹 | `tools/record.py` | 8 个轨迹工具 |
| 配置 | `tools/configure.py` | 5 个配置工具 |
| 安全 | `tools/emergency.py` | 9 个安全工具 |

## 安装

### 前提条件

- Python >= 3.10
- 已安装 `litearm-python`

### 安装步骤

```bash
cd litearm-dsh
pip install -e ".[dev]"
```

依赖项：
- `litearm-python` — LiteArm 机械臂 Python SDK
- `deepseek-harness-sdk` — DeepSeek Harness Python SDK（可选，用于 Harness 集成）
- `openai` — OpenAI SDK（用于 DeepSeek API 直连 tool calling 回退方案）

### 配置 API Key

```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

API Key 从 [DeepSeek 平台](https://platform.deepseek.com/) 获取。

## 快速开始

### 1. 确保机械臂服务已启动

在机械臂控制器（如地瓜）上：

```bash
python -m litearm_server --endpoint tcp/0.0.0.0:7447 --iface can0
```

### 2. 启动 CLI

```bash
# 本机连接（机械臂服务在本机）
python -m litearm_dsh

# 远程连接（机械臂服务在控制器上）
python -m litearm_dsh --endpoint tcp/192.168.31.237:7447

# 使用 DeepSeek Reasoner 模型（推理能力强，适合复杂任务）
python -m litearm_dsh --model deepseek-reasoner
```

### 3. 对话示例

```
🤖 > 读取当前机械臂状态

状态: ready
关节角(q): ['0.000', '0.523', '0.000', '-1.047', '0.000', '0.628', '0.000']

🤖 > 回到零位

move_home 完成: ok=True

🤖 > 向前移动 10cm，先帮我算一下 IK

IK 成功: q=['0.000', '0.432', '0.000', '-0.987', '0.000', '0.554', '0.000']
move_joints 完成: q_target=[...], speed=0.5, ok=True
```

## 使用方式

### CLI 交互模式

进入交互式对话，逐条输入自然语言指令：

```bash
python -m litearm_dsh --endpoint tcp/192.168.31.237:7447
```

输入 `quit`、`exit` 或 `q` 退出，按 `Ctrl+C` 也可退出。

### 单次命令模式

不进入交互模式，直接执行一条指令：

```bash
python -m litearm_dsh --prompt "回到零位，然后读取状态"
python -m litearm_dsh --prompt "把灵巧手打开" --endpoint tcp/192.168.31.237:7447
```

### Python API

#### 单次调用

```python
from litearm_dsh import run_agent

result = run_agent(
    "把机械臂回到零位，然后移动到 [0.0, 0.5, 0.0, -1.0, 0.0, 0.6, 0.0]",
    endpoint="tcp/192.168.31.237:7447",
)
print(result)
```

#### 多轮交互

```python
from litearm_dsh import LiteArmAgent

agent = LiteArmAgent(endpoint="tcp/192.168.31.237:7447")
try:
    # 连续对话，LLM 会记住上下文
    print(agent.run("读取当前状态"))
    print(agent.run("回到零位"))
    print(agent.run("灵巧手做捏取手势"))
    print(agent.run("急停！"))
finally:
    agent.close()
```

#### 自定义模型和 API Key

```python
agent = LiteArmAgent(
    endpoint="tcp/192.168.31.237:7447",
    model="deepseek-reasoner",        # 或 deepseek-chat
    api_key="sk-...",                 # 不传则读环境变量 DEEPSEEK_API_KEY
    verbose=True,                     # 打印工具调用详情
)
```

#### 程序化 CLI

```python
from litearm_dsh import run_cli

run_cli(endpoint="tcp/192.168.31.237:7447", verbose=True)
```

## 工具参考

以下列出所有 42 个工具函数，供了解 LLM 可用的能力范围。

### 运动控制

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `move_joints` | 关节空间运动到目标构型 | `q_target` (7 关节角), `speed` (0.01~1.0) |
| `move_linear` | 笛卡尔直线运动 | `pose_goal` (位姿), `speed` |
| `move_arc` | 笛卡尔圆弧运动 | `pose_via` (途经点), `pose_goal` (终点) |
| `move_waypoints` | 多航点运动 | `poses_goal` (位姿列表) |
| `move_home` | 回零位 | `speed` (默认 0.3) |
| `hold_position` | 原地持位 | `kp_scale` (刚度倍数) |
| `zero_gravity` | 零重力拖动模式 | `duration_s` (默认 10s) |
| `impedance_control` | 阻抗控制 | `q_des`, `K`, `B`, `mode` (joint/cartesian) |
| `joint_follow` | 关节跟随 | `duration_s`, `speed_limit` |
| `direct_mit_control` | 直接 MIT 电机控制 ⚠️ | `kp`, `kd`, `q_ref`, `dq_ref`, `tau_ff` |

#### 关节构型参考

7 个关节，单位弧度：

| 关节 | 范围 | 典型值 |
|------|------|--------|
| J0 | [-2.97, 2.97] | 0.0 |
| J1 | [-1.75, 1.75] | 0.5 |
| J2 | [-2.97, 2.97] | 0.0 |
| J3 | [-3.05, 3.05] | -1.0 |
| J4 | [-2.97, 2.97] | 0.0 |
| J5 | [-1.75, 1.75] | 0.6 |
| J6 | [-2.97, 2.97] | 0.0 |

#### 位姿格式

```python
pose = [
    [px, py, pz],                          # 位置 (米)
    [                                      # 3x3 旋转矩阵
        [r00, r01, r02],
        [r10, r11, r12],
        [r20, r21, r22],
    ],
]
```

### 状态查询

| 工具名 | 功能 | 是否运动 |
|--------|------|----------|
| `get_arm_state` | 关节角/速度/力矩/故障/状态/watchdog | ❌ |
| `get_tcp_pose` | 末端位姿（位置 + 旋转矩阵） | ❌ |
| `compute_fk` | 正运动学（关节角 → 位姿） | ❌ |
| `compute_ik` | 逆运动学（位姿 → 关节角） | ❌ |
| `get_system_info` | CPU/内存/板温/运行时间 | ❌ |
| `get_logs` | 查询 server 端日志（分页） | ❌ |

### 末端操作

| 工具名 | 功能 | 操作类型 |
|--------|------|----------|
| `hand_control` | 灵巧手控制 | `open` / `close` / `gesture` / `finger_move` / `set_force` / `set_speed` / `set_torque` / `get_state` / `list_gestures` / `clear_faults` |
| `gripper_control` | 夹爪控制 | `set_width` / `get_width` / `open` / `close` |
| `teach_pendant` | 示教板读取 | `get_joints` / `get_buttons` |
| `teleop_control` | 遥操控制 | `enter` / `exit` / `status` |

#### 灵巧手支持的手势

`open` `close` `pinch` `fist` `point` `peace` `ok` `thumb_up` `grip` `tripod` `spread` `rest`

### 轨迹

| 工具名 | 功能 |
|--------|------|
| `record_trajectory` | 零重力拖动录制轨迹 |
| `replay_trajectory` | 回放关节路径或已保存轨迹 |
| `manage_trajectories` | 列出/保存/删除轨迹 |
| `start_recording` | 开始录制（运动中录制） |
| `stop_recording` | 停止录制 |
| `discard_recording` | 丢弃当前录制 |
| `get_recording_state` | 查询录制状态 |
| `get_playback_state` | 查询回放状态 |

### 配置

| 工具名 | 功能 |
|--------|------|
| `set_arm_params` | 设置/查询 PD 增益、负载、安装姿态 |
| `set_limits` | 设置/查询关节限位、笛卡尔限位、碰撞配置、零位偏移 |
| `set_end_effector` | 设置末端执行器配置 |
| `get_end_effector` | 查询末端执行器配置 |
| `manage_device` | 末端设备管理（列出/连接/断开/查询） |

### 安全

| 工具名 | 功能 | 风险等级 |
|--------|------|----------|
| `emergency_stop` | 急停（独立通道，立即停止） | 安全 |
| `clear_stop` | 清除急停状态 | 安全 |
| `enable_motors` | 使能电机 | 安全 |
| `disable_motors` | 失能电机 ⚠️ | 高危 |
| `clear_faults` | 清除电机故障 | 安全 |
| `reconnect_arm` | 重连硬件 | 安全 |
| `restart_service` | 重启控制服务 ⚠️ | 高危 |
| `get_guards` | 查询护栏配置 | 安全 |
| `set_guards` | 设置护栏配置 ⚠️ | 谨慎 |

## 安全架构

三层防护，纵深防御：

### 第 1 层：LLM 层（system prompt）

- 运动前必须先查询状态
- 默认保守速度 (speed=0.3~0.5)
- 高危操作需用户明确确认
- 随时可调用 emergency_stop

### 第 2 层：工具层（safety_gate.py）

**参数校验（拒绝不合理参数）：**
- 关节角范围检查（±限位 + 0.1 rad 余量）
- 速度上限 2.0（超出自动钳制）
- 负载质量 0~10 kg
- 夹爪宽度 0.0~1.0
- 灵巧手力 0.0~1.0
- 持续时间上限 300 秒
- 位姿格式校验（3 元素位置 + 3x3 旋转矩阵）
- NaN/Inf 拒绝

**高危操作警告：**
- `disable_motors` — 警告坠落风险
- `restart_service` — 警告中断风险
- `direct_mit_control` — 警告绕过运动规划

### 第 3 层：server 层（litearm-server 硬防护）

- watchdog 超时自动急停
- 关节速度斜率限制
- 关节限位硬限制
- 自碰撞检测
- 笛卡尔限位

## 配置

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必填 |
| `LITEARM_ENDPOINT` | litearm-server 的 zenoh 端点 | `tcp/127.0.0.1:7447` |

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--endpoint`, `-e` | litearm-server 端点 | 环境变量 `LITEARM_ENDPOINT` 或 `tcp/127.0.0.1:7447` |
| `--arm-id` | 机械臂标识 | `armA` |
| `--model`, `-m` | DeepSeek 模型 | `deepseek-chat` |
| `--api-key` | DeepSeek API 密钥 | 环境变量 `DEEPSEEK_API_KEY` |
| `--verbose`, `-v` | 打印工具调用详情 | 关闭 |
| `--prompt`, `-p` | 单次命令模式 | 交互模式 |

### 模型选择

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| `deepseek-chat` | 快速、便宜 | 日常控制、简单任务 |
| `deepseek-reasoner` | 推理能力强、较慢 | 复杂任务规划、多步操作 |

## 常见问题

### Q: 连接失败怎么办？

1. 确认 litearm-server 已启动：`python -m litearm_server --endpoint tcp/0.0.0.0:7447 --iface can0`
2. 确认网络互通：`ping <控制器 IP>`
3. 确认 endpoint 格式正确：`tcp/<IP>:<端口>`

### Q: 运动不执行或报错？

1. 先用 `get_arm_state` 查看当前状态
2. 如果状态是 `fault`，用 `clear_faults` 清除故障
3. 如果状态是 `stopping`，用 `clear_stop` 清除急停
4. 如果状态是 `disconnected`，用 `reconnect_arm` 重连

### Q: LLM 输出了不合理的关节角怎么办？

safety_gate 会自动拦截超出限位的关节角并返回错误信息。LLM 会读取错误信息后重试。如果持续不合理，使用 `emergency_stop` 急停。

### Q: 如何回退到直接 API 调用模式？

如果 DeepSeek Harness SDK 不可用，系统会自动回退到 OpenAI 兼容的 tool calling 模式。这个行为是自动的，无需手动配置。

### Q: 支持多个机械臂吗？

通过 `--arm-id` 参数指定不同的 arm_id：

```bash
python -m litearm_dsh --arm-id armA --endpoint tcp/192.168.31.139:7447
python -m litearm_dsh --arm-id armB --endpoint tcp/192.168.31.72:7447
```

## 开发

### 运行测试

```bash
python -m pytest tests/ -v
```

### 项目结构

```
litearm-dsh/
├── pyproject.toml
├── README.md
├── README.zh-CN.md
├── .gitignore
├── src/litearm_dsh/
│   ├── __init__.py
│   ├── __main__.py          # CLI 入口
│   ├── agent.py             # Agent 主逻辑
│   ├── arm_handle.py        # 连接管理
│   ├── safety_gate.py       # 安全校验
│   └── tools/
│       ├── __init__.py      # 工具注册表
│       ├── move.py          # 运动控制
│       ├── query.py         # 状态查询
│       ├── operate.py       # 末端操作
│       ├── record.py        # 轨迹
│       ├── configure.py     # 配置
│       └── emergency.py     # 安全
└── tests/
    └── test_litearm_dsh.py
```

## License

Proprietary