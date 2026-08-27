"""Arm connection handle — singleton management of litearm.Arm.

Provides a single global Arm instance shared across all tool calls.
Handles connect / reconnect / health check / close.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

import litearm

from .safety_gate import SafetyGate

_LOCK = threading.Lock()
_ARM: Optional[litearm.Arm] = None
_ENDPOINT: str = "tcp/127.0.0.1:7447"
_ARM_ID: str = "armA"


class ArmHandle:
    """Singleton wrapper around litearm.Arm for shared use across tool calls."""

    @staticmethod
    def get() -> litearm.Arm:
        """Get the global Arm instance (connect if needed). Thread-safe."""
        global _ARM
        with _LOCK:
            if _ARM is None:
                _ARM = litearm.Arm(endpoint=_ENDPOINT, arm_id=_ARM_ID)
            return _ARM

    @staticmethod
    def reset(endpoint: Optional[str] = None, arm_id: Optional[str] = None) -> litearm.Arm:
        """Close existing connection and create a new one."""
        global _ARM, _ENDPOINT, _ARM_ID
        with _LOCK:
            if _ARM is not None:
                try:
                    _ARM.close()
                except Exception:
                    pass
            if endpoint is not None:
                _ENDPOINT = endpoint
            if arm_id is not None:
                _ARM_ID = arm_id
            _ARM = litearm.Arm(endpoint=_ENDPOINT, arm_id=_ARM_ID)
            return _ARM

    @staticmethod
    def close() -> None:
        """Close the global Arm connection."""
        global _ARM
        with _LOCK:
            if _ARM is not None:
                try:
                    _ARM.close()
                except Exception:
                    pass
                _ARM = None

    @staticmethod
    def get_state() -> Optional[Dict[str, Any]]:
        """Get cached arm state (non-blocking)."""
        arm = ArmHandle.get()
        return arm.get_state()

    @staticmethod
    def get_state_summary() -> str:
        """Return a human-readable state summary for the LLM."""
        state = ArmHandle.get_state()
        if state is None:
            return "无状态数据（server 可能未连接或未就绪）"
        try:
            q = state.get("q", [])
            dq = state.get("dq", [])
            tau = state.get("tau", [])
            arm_state = state.get("state", "unknown")
            fault = state.get("fault", [])
            temps = state.get("temps", [])

            lines = [f"状态: {arm_state}"]
            if q:
                lines.append(f"关节角(q): {[f'{v:.3f}' for v in q]}")
            if dq:
                lines.append(f"关节速度(dq): {[f'{v:.3f}' for v in dq]}")
            if tau:
                lines.append(f"关节力矩(tau): {[f'{v:.3f}' for v in tau]}")
            if fault:
                lines.append(f"故障: {fault}")
            if temps:
                lines.append(f"温度: {temps}")
            wd = state.get("watchdog", {})
            if wd and wd.get("tripped"):
                lines.append("⚠️ watchdog 已触发!")
            return "\n".join(lines)
        except Exception as e:
            return f"状态解析失败: {e}"


# ── Convenience functions ──────────────────────────────────────────────────────

def get_arm() -> litearm.Arm:
    """Get the global Arm instance."""
    return ArmHandle.get()


def reset_arm(endpoint: Optional[str] = None, arm_id: Optional[str] = None) -> litearm.Arm:
    """Reset the global Arm connection."""
    return ArmHandle.reset(endpoint, arm_id)