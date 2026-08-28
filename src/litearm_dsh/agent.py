"""LiteArmAgent — DeepSeek Harness agent for LiteArm robotic arm control.

Two modes:
1. CLI interactive: lite_arm CLI command (via dsh plugin)
2. Python API: LiteArmAgent.run() for programmatic use
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Union

from .arm_handle import ArmHandle
from .tools import TOOLS, TOOL_CATEGORIES

# ── System prompt ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个 LiteArm 7 自由度机械臂控制助手。你可以通过调用工具函数来控制真实机械臂。

## 重要安全规则

1. **运动前先查询状态** — 在执行任何运动指令前，先调用 get_arm_state 了解当前状态。
2. **保守速度** — 首次运动建议 speed=0.3~0.5，确认安全后再提高。
3. **随时可急停** — 如果用户说"停"、"急停"、"stop"，立即调用 emergency_stop。
4. **高危操作需确认** — disable_motors、restart_service、direct_mit_control 需要用户明确确认。
5. **错误处理** — 工具调用失败时，分析错误信息，尝试调整参数或告知用户。
6. **等待运动完成** — 运动指令是阻塞的，完成后才会返回结果。

## 工具分类

### 运动控制
- move_joints: 关节空间运动到目标构型（最常用）
- move_linear: 笛卡尔直线运动
- move_arc: 圆弧运动
- move_waypoints: 多航点运动
- move_home: 回零位
- hold_position: 原地持位
- zero_gravity: 零重力拖动模式
- impedance_control: 阻抗控制
- joint_follow: 关节跟随
- direct_mit_control: 直接 MIT 电机控制（⚠️ 高危）

### 状态查询
- get_arm_state: 读取关节角/速度/力矩/故障/状态
- get_tcp_pose: 读取末端位姿
- compute_fk: 正运动学计算
- compute_ik: 逆运动学计算
- get_system_info: CPU/内存/温度
- get_logs: 查询日志

### 末端操作
- hand_control: 灵巧手控制（开/合/手势/力控）
- gripper_control: 夹爪控制（宽度/开合）
- teach_pendant: 示教板读取
- teleop_control: 遥操控制

### 轨迹
- record_trajectory: 拖动录制轨迹
- replay_trajectory: 回放轨迹
- manage_trajectories: 轨迹管理（列出/保存/删除）
- start_recording / stop_recording: 录制控制

### 配置
- set_arm_params: PD 增益/负载/安装姿态
- set_limits: 关节/笛卡尔限位/碰撞配置
- set_end_effector / get_end_effector: 末端执行器配置
- manage_device: 末端设备管理

### 安全
- emergency_stop: 急停
- clear_stop: 清除急停
- enable_motors / disable_motors: 使能/失能
- clear_faults: 清除故障
- reconnect_arm: 重连硬件
- restart_service: 重启服务
- get_guards / set_guards: 护栏配置

## 工作流程

1. 用户提出需求 → 分析需要哪些工具
2. 查询当前状态 → get_arm_state
3. 规划运动 → 如需 IK 计算使用 compute_ik
4. 执行运动 → 选择合适的速度
5. 验证结果 → 再次查询状态确认

## 位姿格式

```
pose = [[px, py, pz], [[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]]]
```

## 关节角

7 个关节，单位弧度，约范围：
- J0: [-2.97, 2.97]
- J1: [-1.75, 1.75]
- J2: [-2.97, 2.97]
- J3: [-3.05, 3.05]
- J4: [-2.97, 2.97]
- J5: [-1.75, 1.75]
- J6: [-2.97, 2.97]

请用中文回复用户。每次回复简洁明了，重点在执行和结果。"""


# ── Agent class ─────────────────────────────────────────────────────────────────

class LiteArmAgent:
    """DeepSeek Harness agent wrapper for LiteArm control.

    Usage::

        agent = LiteArmAgent(endpoint="tcp/192.168.31.237:7447")
        result = agent.run("把机械臂回到零位")
        print(result)

        # CLI mode
        agent.cli()
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        arm_id: str = "armA",
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        verbose: bool = False,
    ):
        """Initialize the LiteArm agent.

        Args:
            endpoint: litearm-server zenoh endpoint (default: env LITEARM_ENDPOINT
                      or tcp/127.0.0.1:7447).
            arm_id: Arm identifier (default "armA").
            model: DeepSeek model to use (default "deepseek-chat").
            api_key: DeepSeek API key (default: env DEEPSEEK_API_KEY).
            verbose: Print tool call details.
        """
        self.endpoint = endpoint or os.environ.get(
            "LITEARM_ENDPOINT", "tcp/127.0.0.1:7447"
        )
        self.arm_id = arm_id
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.verbose = verbose

        # Initialize arm connection
        ArmHandle.reset(endpoint=self.endpoint, arm_id=self.arm_id)

    def _build_tools_for_harness(self) -> Dict[str, Callable]:
        """Return the tools dict in a format compatible with DeepSeek Harness."""
        return dict(TOOLS)

    def run(self, prompt: str) -> str:
        """Run a single prompt against the agent. Returns the LLM response text.

        This is a programmatic API — use for automation and evaluation.
        Tries DeepSeek Harness SDK first; falls back to direct API on any failure.
        """
        try:
            import deepseek_harness  # noqa: F401
            return self._run_via_harness(prompt)
        except (ImportError, Exception) as e:
            if self.verbose:
                print(f"  [info] Harness SDK 不可用 ({e})，回退到直接 API 调用", file=sys.stderr)
            return self._run_via_direct_api(prompt)

    def _run_via_harness(self, prompt: str) -> str:
        """Run via DeepSeek Harness Python SDK."""
        from deepseek_harness import DeepSeekHarness

        # DeepSeek Harness expects a cordis.yml config
        # We use a minimal config that points to our custom tools
        config_path = self._write_harness_config()

        try:
            with DeepSeekHarness(config=config_path) as harness:
                result = harness.run(prompt)
                return str(result)
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)

    def _run_via_direct_api(self, prompt: str) -> str:
        """Fallback: use DeepSeek API directly with tool calling loop."""
        if not self.api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY not set. Set it in env or pass api_key= to LiteArmAgent."
            )

        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
        )

        tools = self._build_openai_tools()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        max_turns = 20
        for _ in range(max_turns):
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                # Append assistant message
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                # Execute each tool call
                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    if self.verbose:
                        print(f"  🔧 {name}({args})", file=sys.stderr)

                    tool_fn = TOOLS.get(name)
                    if tool_fn:
                        try:
                            result = tool_fn(**args)
                        except Exception as e:
                            result = f"工具执行异常: {type(e).__name__}: {e}"
                    else:
                        result = f"未知工具: {name}"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result),
                    })
            else:
                # Final response
                return msg.content or ""

        return "已达到最大交互轮数。"

    def _build_openai_tools(self) -> List[Dict[str, Any]]:
        """Build OpenAI-compatible tool definitions from our tool functions."""
        import inspect

        def _resolve_type(annotation: Any) -> str:
            """Resolve a Python type annotation to JSON Schema type string."""
            if annotation is inspect.Parameter.empty:
                return "string"
            # Handle Optional[X] (Union[X, None]) and other Union types
            origin = getattr(annotation, "__origin__", None)
            args = getattr(annotation, "__args__", ())
            if origin is Union or origin is getattr(Union, "__origin__", None):
                # Pick the first non-NoneType arg
                for arg in args:
                    if arg is not type(None):  # noqa: E721
                        return _resolve_type(arg)
                return "string"
            # Handle List[X]
            if origin is list or origin is List:
                return "array"
            # Handle Dict
            if origin is dict or origin is Dict:
                return "object"
            # Direct type comparison
            if annotation is float or annotation is int:
                return "number"
            if annotation is bool:
                return "boolean"
            if annotation is str:
                return "string"
            if annotation is dict:
                return "object"
            if annotation is list:
                return "array"
            if annotation is Any:
                return "string"
            return "string"

        tools = []
        for name, fn in TOOLS.items():
            sig = inspect.signature(fn)
            doc = fn.__doc__ or ""
            desc_lines = doc.strip().split("\n\n")
            description = desc_lines[0] if desc_lines else name

            properties = {}
            required = []
            for pname, param in sig.parameters.items():
                if pname in ("self", "cls"):
                    continue
                prop = {"type": _resolve_type(param.annotation)}
                if prop["type"] == "array":
                    prop["items"] = {"type": "number"}

                # Extract param description from docstring
                for line in doc.split("\n"):
                    line = line.strip()
                    if line.startswith(f"{pname}:") or line.startswith(f"{pname} "):
                        prop["description"] = line.split(":", 1)[-1].strip() if ":" in line else ""
                        break

                if param.default is inspect.Parameter.empty:
                    required.append(pname)

                properties[pname] = prop

            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })

        return tools

    def _write_harness_config(self) -> str:
        """Write a temporary cordis.yml for DeepSeek Harness."""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".yml", prefix="litearm-dsh-")
        os.close(fd)
        # Minimal config — actual tool registration depends on SDK version
        with open(path, "w") as f:
            f.write(f"""# litearm-dsh auto-generated config
plugins:
  "@deepseek-ai/dsh-tools/bash": {{}}
  "@deepseek-ai/dsh-tools/file": {{}}
""")
        return path

    def cli(self) -> None:
        """Interactive CLI loop — chat with the agent in terminal."""
        print("=" * 60)
        print("  LiteArm DSH — LLM-driven robotic arm control")
        print(f"  endpoint: {self.endpoint}")
        print(f"  model:    {self.model}")
        print("=" * 60)
        print()
        print("输入自然语言指令控制机械臂。输入 'quit' 退出。")
        print()

        # Check connection
        try:
            state = ArmHandle.get_state_summary()
            print(f"[状态] {state}")
            print()
        except Exception as e:
            print(f"[警告] 无法连接机械臂: {e}")
            print()

        while True:
            try:
                user_input = input("🤖 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出。")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("退出。")
                break

            print()
            result = self.run(user_input)
            print(result)
            print()

    def close(self) -> None:
        """Close the arm connection."""
        ArmHandle.close()


# ── Convenience functions ──────────────────────────────────────────────────────

def run_agent(
    prompt: str,
    endpoint: Optional[str] = None,
    model: str = "deepseek-chat",
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Run a single prompt and return the result.

    Convenience function for one-shot programmatic use.
    """
    agent = LiteArmAgent(
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        verbose=verbose,
    )
    try:
        return agent.run(prompt)
    finally:
        agent.close()


def run_cli(
    endpoint: Optional[str] = None,
    model: str = "deepseek-chat",
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """Start the interactive CLI.

    Convenience function for CLI entry point.
    """
    agent = LiteArmAgent(
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        verbose=verbose,
    )
    try:
        agent.cli()
    finally:
        agent.close()