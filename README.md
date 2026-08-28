# litearm-dsh

DeepSeek Harness-powered LiteArm robotic arm control — control a real robotic arm with natural language.

```
You: "Go to home position, then draw a 10cm square"
LLM: plan → get_arm_state → move_home → compute_ik×4 → move_linear×4 → done ✅
```

## Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI Interactive Mode](#cli-interactive-mode)
  - [Single Prompt Mode](#single-prompt-mode)
  - [Python API](#python-api)
- [Tool Reference](#tool-reference)
  - [Motion Control](#motion-control)
  - [State Query](#state-query)
  - [End-Effector Operations](#end-effector-operations)
  - [Trajectories](#trajectories)
  - [Configuration](#configuration)
  - [Safety](#safety)
- [Safety Architecture](#safety-architecture)
- [Configuration](#configuration-1)
- [FAQ](#faq)
- [Development](#development)

## Architecture

```
┌──────────────────────────────────────────────────┐
│ DeepSeek API (deepseek-chat / deepseek-reasoner) │
│ LLM reasoning + tool selection                    │
└──────────────────────┬───────────────────────────┘
                       │ HTTPS
┌──────────────────────┴───────────────────────────┐
│ litearm-dsh (Python)                              │
│                                                   │
│  ┌───────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ agent.py  │  │   tools/     │  │ safety_gate │ │
│  │ Harness/  │──│ 6 groups     │──│ param       │ │
│  │ OpenAI    │  │ 42 tools     │  │ validation  │ │
│  └───────────┘  └──────────────┘  └─────┬──────┘ │
│                                         │         │
│                              ┌──────────┴──────┐  │
│                              │ arm_handle.py   │  │
│                              │ Arm singleton   │  │
│                              └──────────┬──────┘  │
└─────────────────────────────────────────┼─────────┘
                                          │ zenoh
┌─────────────────────────────────────────┴─────────┐
│ litearm-server                                     │
│ watchdog · slew limit · joint limits · collision   │
└─────────────────────────────────────────┬─────────┘
                                          │ CAN
┌─────────────────────────────────────────┴─────────┐
│ LiteArm 7-DOF Robotic Arm                          │
└───────────────────────────────────────────────────┘
```

### Module Overview

| Module | File | Responsibility |
|--------|------|----------------|
| Agent Entry | `agent.py` | DeepSeek Harness SDK / OpenAI tool calling dual-path |
| Safety Gate | `safety_gate.py` | 30+ parameter validation methods, unified interceptor |
| Connection | `arm_handle.py` | litearm.Arm singleton, thread-safe |
| Motion | `tools/move.py` | 10 motion tools |
| Query | `tools/query.py` | 6 query tools |
| Operate | `tools/operate.py` | 4 end-effector tools |
| Record | `tools/record.py` | 8 trajectory tools |
| Configure | `tools/configure.py` | 5 configuration tools |
| Emergency | `tools/emergency.py` | 9 safety tools |

## Installation

### Prerequisites

- Python >= 3.10
- `litearm-python` installed

### Install

```bash
cd litearm-dsh
pip install -e ".[dev]"
```

Dependencies:
- `litearm-python` — LiteArm Python client SDK
- `deepseek-harness-sdk` — DeepSeek Harness Python SDK (optional, for Harness integration)
- `openai` — OpenAI SDK (for DeepSeek API direct tool calling fallback)

### Set API Key

```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Get your API key from the [DeepSeek Platform](https://platform.deepseek.com/).

## Quick Start

### 1. Ensure litearm-server is running

On the arm controller:

```bash
python -m litearm_server --endpoint tcp/0.0.0.0:7447 --iface can0
```

### 2. Launch CLI

```bash
# Local connection (server on same machine)
python -m litearm_dsh

# Remote connection (server on arm controller)
python -m litearm_dsh --endpoint tcp/192.168.31.237:7447

# Use DeepSeek Reasoner for complex tasks
python -m litearm_dsh --model deepseek-reasoner
```

### 3. Example Session

```
🤖 > read the current arm state

State: ready
Joint positions (q): ['0.000', '0.523', '0.000', '-1.047', '0.000', '0.628', '0.000']

🤖 > go to home position

move_home complete: ok=True

🤖 > move forward 10cm, compute IK first

IK success: q=['0.000', '0.432', '0.000', '-0.987', '0.000', '0.554', '0.000']
move_joints complete: q_target=[...], speed=0.5, ok=True
```

## Usage

### CLI Interactive Mode

Enter an interactive chat session, type natural language commands one at a time:

```bash
python -m litearm_dsh --endpoint tcp/192.168.31.237:7447
```

Type `quit`, `exit`, or `q` to exit. `Ctrl+C` also works.

### Single Prompt Mode

Execute a single command without entering interactive mode:

```bash
python -m litearm_dsh --prompt "go home and read state"
python -m litearm_dsh --prompt "open the hand" --endpoint tcp/192.168.31.237:7447
```

### Python API

#### One-shot call

```python
from litearm_dsh import run_agent

result = run_agent(
    "Go to home position, then move to [0.0, 0.5, 0.0, -1.0, 0.0, 0.6, 0.0]",
    endpoint="tcp/192.168.31.237:7447",
)
print(result)
```

#### Multi-turn conversation

```python
from litearm_dsh import LiteArmAgent

agent = LiteArmAgent(endpoint="tcp/192.168.31.237:7447")
try:
    # The LLM remembers context across calls
    print(agent.run("Read current state"))
    print(agent.run("Go home"))
    print(agent.run("Pinch with the hand"))
    print(agent.run("Emergency stop!"))
finally:
    agent.close()
```

#### Custom model and API key

```python
agent = LiteArmAgent(
    endpoint="tcp/192.168.31.237:7447",
    model="deepseek-reasoner",        # or deepseek-chat
    api_key="sk-...",                 # defaults to env DEEPSEEK_API_KEY
    verbose=True,                     # print tool call details
)
```

#### Programmatic CLI

```python
from litearm_dsh import run_cli

run_cli(endpoint="tcp/192.168.31.237:7447", verbose=True)
```

## Tool Reference

All 42 tools available to the LLM are listed below.

### Motion Control

| Tool | Function | Key Parameters |
|------|----------|----------------|
| `move_joints` | Joint-space motion to target configuration | `q_target` (7 joint angles), `speed` (0.01~1.0) |
| `move_linear` | Cartesian straight-line motion | `pose_goal` (pose), `speed` |
| `move_arc` | Cartesian circular arc motion | `pose_via` (via point), `pose_goal` (end point) |
| `move_waypoints` | Multi-waypoint motion with corner blending | `poses_goal` (list of poses) |
| `move_home` | Home all joints to zero | `speed` (default 0.3) |
| `hold_position` | Hold current position with increased stiffness | `kp_scale` (stiffness multiplier) |
| `zero_gravity` | Free-drag mode (gravity compensation only) | `duration_s` (default 10s) |
| `impedance_control` | Spring-damper impedance control | `q_des`, `K`, `B`, `mode` (joint/cartesian) |
| `joint_follow` | Low-stiffness joint following | `duration_s`, `speed_limit` |
| `direct_mit_control` | Direct MIT motor control ⚠️ | `kp`, `kd`, `q_ref`, `dq_ref`, `tau_ff` |

#### Joint Configuration Reference

7 joints, in radians:

| Joint | Range | Typical |
|-------|-------|---------|
| J0 | [-2.97, 2.97] | 0.0 |
| J1 | [-1.75, 1.75] | 0.5 |
| J2 | [-2.97, 2.97] | 0.0 |
| J3 | [-3.05, 3.05] | -1.0 |
| J4 | [-2.97, 2.97] | 0.0 |
| J5 | [-1.75, 1.75] | 0.6 |
| J6 | [-2.97, 2.97] | 0.0 |

#### Pose Format

```python
pose = [
    [px, py, pz],                          # position (meters)
    [                                      # 3x3 rotation matrix
        [r00, r01, r02],
        [r10, r11, r12],
        [r20, r21, r22],
    ],
]
```

### State Query

| Tool | Function | Moves Arm? |
|------|----------|------------|
| `get_arm_state` | Joint angles/velocities/torques/faults/state/watchdog | ❌ No |
| `get_tcp_pose` | TCP pose (position + rotation matrix) | ❌ No |
| `compute_fk` | Forward kinematics (joints → pose) | ❌ No |
| `compute_ik` | Inverse kinematics (pose → joints) | ❌ No |
| `get_system_info` | CPU/memory/board temp/uptime | ❌ No |
| `get_logs` | Query server logs (paginated) | ❌ No |

### End-Effector Operations

| Tool | Function | Actions |
|------|----------|---------|
| `hand_control` | Dexterous hand control | `open` / `close` / `gesture` / `finger_move` / `set_force` / `set_speed` / `set_torque` / `get_state` / `list_gestures` / `clear_faults` |
| `gripper_control` | Gripper control | `set_width` / `get_width` / `open` / `close` |
| `teach_pendant` | Teach pendant reading | `get_joints` / `get_buttons` |
| `teleop_control` | Teleoperation control | `enter` / `exit` / `status` |

#### Supported Hand Gestures

`open` `close` `pinch` `fist` `point` `peace` `ok` `thumb_up` `grip` `tripod` `spread` `rest`

### Trajectories

| Tool | Function |
|------|----------|
| `record_trajectory` | Record trajectory in zero-gravity drag mode |
| `replay_trajectory` | Replay a joint path or saved trajectory |
| `manage_trajectories` | List/save/delete trajectories |
| `start_recording` | Start recording (in-motion recording) |
| `stop_recording` | Stop recording |
| `discard_recording` | Discard current recording |
| `get_recording_state` | Query recording state |
| `get_playback_state` | Query playback state |

### Configuration

| Tool | Function |
|------|----------|
| `set_arm_params` | Get/set PD gains, payload, installation orientation |
| `set_limits` | Get/set joint limits, cartesian limits, collision config, zero offsets |
| `set_end_effector` | Set end-effector configuration |
| `get_end_effector` | Get end-effector configuration |
| `manage_device` | End-effector device management (list/connect/disconnect/query) |

### Safety

| Tool | Function | Risk Level |
|------|----------|------------|
| `emergency_stop` | Emergency stop (dedicated channel, immediate) | Safe |
| `clear_stop` | Clear stop condition | Safe |
| `enable_motors` | Enable motors | Safe |
| `disable_motors` | Disable motors ⚠️ | High Risk |
| `clear_faults` | Clear motor faults | Safe |
| `reconnect_arm` | Reconnect hardware | Safe |
| `restart_service` | Restart control service ⚠️ | High Risk |
| `get_guards` | Query guard configuration | Safe |
| `set_guards` | Set guard configuration ⚠️ | Caution |

## Safety Architecture

Three-layer defense-in-depth:

### Layer 1: LLM (system prompt)

- Always query state before any motion
- Conservative default speeds (0.3~0.5)
- High-risk operations require explicit user confirmation
- emergency_stop available at any time

### Layer 2: Tool Layer (safety_gate.py)

**Parameter validation (rejects invalid parameters):**
- Joint angle range check (±limit + 0.1 rad margin)
- Speed cap at 2.0 (auto-clamped)
- Payload mass 0~10 kg
- Gripper width 0.0~1.0
- Hand force 0.0~1.0
- Duration cap at 300 seconds
- Pose format validation (3-element position + 3x3 rotation matrix)
- NaN/Inf rejection

**High-risk operation warnings:**
- `disable_motors` — warns about gravity drop
- `restart_service` — warns about interruption
- `direct_mit_control` — warns about bypassing motion planning

### Layer 3: Server Layer (litearm-server hard enforcement)

- Watchdog timeout → automatic emergency stop
- Joint velocity slew rate limiting
- Joint limit hard enforcement
- Self-collision detection
- Cartesian limit enforcement

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API key | Required |
| `LITEARM_ENDPOINT` | litearm-server zenoh endpoint | `tcp/127.0.0.1:7447` |

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--endpoint`, `-e` | litearm-server endpoint | env `LITEARM_ENDPOINT` or `tcp/127.0.0.1:7447` |
| `--arm-id` | Arm identifier | `armA` |
| `--model`, `-m` | DeepSeek model | `deepseek-chat` |
| `--api-key` | DeepSeek API key | env `DEEPSEEK_API_KEY` |
| `--verbose`, `-v` | Print tool call details | Off |
| `--prompt`, `-p` | Single prompt mode | Interactive mode |

### Model Selection

| Model | Characteristics | Use Case |
|-------|-----------------|----------|
| `deepseek-chat` | Fast, cost-effective | Daily control, simple tasks |
| `deepseek-reasoner` | Strong reasoning, slower | Complex task planning, multi-step operations |

## FAQ

### Q: Connection fails?

1. Confirm litearm-server is running: `python -m litearm_server --endpoint tcp/0.0.0.0:7447 --iface can0`
2. Confirm network connectivity: `ping <controller IP>`
3. Verify endpoint format: `tcp/<IP>:<port>`

### Q: Motion doesn't execute or returns errors?

1. Check current state with `get_arm_state`
2. If state is `fault`, use `clear_faults`
3. If state is `stopping`, use `clear_stop`
4. If state is `disconnected`, use `reconnect_arm`

### Q: What if the LLM outputs unreasonable joint angles?

The safety_gate automatically intercepts out-of-limit joint angles and returns an error message. The LLM reads the error and retries. If problems persist, use `emergency_stop`.

### Q: How does the fallback to direct API work?

If DeepSeek Harness SDK is unavailable, the system automatically falls back to OpenAI-compatible tool calling mode. This is automatic — no manual configuration needed.

### Q: Can I control multiple arms?

Use different `--arm-id` values:

```bash
python -m litearm_dsh --arm-id armA --endpoint tcp/192.168.31.139:7447
python -m litearm_dsh --arm-id armB --endpoint tcp/192.168.31.72:7447
```

## Development

### Run Tests

```bash
python -m pytest tests/ -v
```

### Project Structure

```
litearm-dsh/
├── pyproject.toml
├── README.md
├── README.zh-CN.md
├── .gitignore
├── src/litearm_dsh/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── agent.py             # Agent core logic
│   ├── arm_handle.py        # Connection management
│   ├── safety_gate.py       # Safety validation
│   └── tools/
│       ├── __init__.py      # Tool registry
│       ├── move.py          # Motion control
│       ├── query.py         # State queries
│       ├── operate.py       # End-effector ops
│       ├── record.py        # Trajectories
│       ├── configure.py     # Configuration
│       └── emergency.py     # Safety
└── tests/
    └── test_litearm_dsh.py
```

## License

Proprietary