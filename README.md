# litearm-dsh

DeepSeek Harness 驱动的 LiteArm 机械臂控制 — 用自然语言控制真实机械臂。

```
你: "把机械臂回到零位，然后画一个正方形"
LLM: 规划 → get_arm_state → move_home → compute_ik×4 → move_linear×4 → 完成
```

## 架构

```
DeepSeek API (LLM)
    │
    ▼
litearm-dsh (Python)
    ├─ agent.py          DeepSeek Harness / OpenAI tool calling
    ├─ safety_gate.py    参数校验 + 高危操作警告
    ├─ arm_handle.py     litearm.Arm 连接单例
    ├─ tools/
    │   ├─ move.py       运动控制 (10 tools)
    │   ├─ query.py      状态查询 (6 tools)
    │   ├─ operate.py    末端操作 (4 tools)
    │   ├─ record.py     轨迹 (5 tools)
    │   ├─ configure.py  配置 (5 tools)
    │   └─ emergency.py  安全 (9 tools)
    │
    ▼
litearm-python SDK
    │ zenoh
    ▼
litearm-server → 机械臂
```

## 安装

```bash
cd litearm-dsh
pip install -e .
```

依赖：
- `litearm-python` — LiteArm 机械臂 Python SDK
- `deepseek-harness-sdk` — DeepSeek Harness Python SDK（可选，用于 Harness 集成）
- `openai` — OpenAI SDK（用于 DeepSeek API 直连 tool calling 回退方案）

## 快速开始

### 1. 设置 API Key

```bash
export DEEPSEEK_API_KEY="sk-..."
```

### 2. 确保 litearm-server 已运行

```bash
# 在机械臂控制器上
python -m litearm_server --endpoint tcp/0.0.0.0:7447 --iface can0
```

### 3. 启动 CLI

```bash
# 本机连接
python -m litearm_dsh

# 远程连接
python -m litearm_dsh --endpoint tcp/192.168.31.237:7447

# 单次命令模式
python -m litearm_dsh --prompt "回到零位"
```

### 4. Python API

```python
from litearm_dsh import run_agent

# 单次调用
result = run_agent(
    "把机械臂回到零位，然后移动到 [0.0, 0.5, 0.0, -1.0, 0.0, 0.6, 0.0]",
    endpoint="tcp/192.168.31.237:7447",
)
print(result)
```

```python
from litearm_dsh import LiteArmAgent

# 多轮交互
agent = LiteArmAgent(endpoint="tcp/192.168.31.237:7447")
try:
    result = agent.run("读取当前状态")
    print(result)
    result = agent.run("向前移动 10cm")
    print(result)
finally:
    agent.close()
```

## 工具分类

### 运动控制
`move_joints` `move_linear` `move_arc` `move_waypoints` `move_home` `hold_position` `zero_gravity` `impedance_control` `joint_follow` `direct_mit_control`

### 状态查询
`get_arm_state` `get_tcp_pose` `compute_fk` `compute_ik` `get_system_info` `get_logs`

### 末端操作
`hand_control` `gripper_control` `teach_pendant` `teleop_control`

### 轨迹
`record_trajectory` `replay_trajectory` `manage_trajectories` `start_recording` `stop_recording`

### 配置
`set_arm_params` `set_limits` `set_end_effector` `get_end_effector` `manage_device`

### 安全
`emergency_stop` `clear_stop` `enable_motors` `disable_motors` `clear_faults` `reconnect_arm` `restart_service` `get_guards` `set_guards`

## 安全

三层防护：

1. **工具层** — `safety_gate.py` 对所有参数做类型/范围/合理性校验，拒绝超标参数；高危操作（disable/restart/direct_mit）返回警告。
2. **server 层** — litearm-server 的 watchdog、斜率限制、限位检查作为硬防护。
3. **LLM 层** — system prompt 明确安全规则：运动前先查询状态、保守速度、随时可急停。

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必填 |
| `LITEARM_ENDPOINT` | litearm-server 端点 | `tcp/127.0.0.1:7447` |

## License

Proprietary