"""Safety gate — unified parameter validation and guard layer.

All tool calls pass through this gate before reaching the arm.
Soft checks catch LLM hallucination; hard checks are enforced by litearm-server.

Reference: [[no-flyaway-hard-line]] — arm must never fly away uncontrollably.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


# ── Joint limits (radians) — LiteArm 7-DOF ────────────────────────────────────

JOINT_LIMITS: List[Tuple[float, float]] = [
    (-2.967, 2.967),   # J0
    (-1.745, 1.745),   # J1
    (-2.967, 2.967),   # J2
    (-3.054, 3.054),   # J3
    (-2.967, 2.967),   # J4
    (-1.745, 1.745),   # J5
    (-2.967, 2.967),   # J6
]

N_JOINTS = 7

# ── Speed / duration limits ──────────────────────────────────────────────────

MAX_SPEED = 2.0        # max speed factor (0..1 nominal, allow slight overshoot)
MIN_SPEED = 0.01
MAX_DURATION_S = 300.0  # max duration for zero_gravity / joint_follow / etc.
MAX_SETTLE_S = 10.0

# ── Payload limits ───────────────────────────────────────────────────────────

MAX_PAYLOAD_MASS = 10.0  # kg
MIN_PAYLOAD_MASS = 0.0

# ── Gripper / hand limits ────────────────────────────────────────────────────

GRIPPER_WIDTH_RANGE = (0.0, 1.0)   # normalized 0-1
HAND_FORCE_RANGE = (0.0, 1.0)      # normalized 0-1

# ── Known gestures ───────────────────────────────────────────────────────────

KNOWN_GESTURES = {
    "open", "close", "pinch", "fist", "point", "peace", "ok", "thumb_up",
    "grip", "tripod", "spread", "rest",
}

# ── Known teleop modes ───────────────────────────────────────────────────────

TELEOP_MODES = {"master", "slave"}


class SafetyGate:
    """Stateless safety validator for all tool parameters."""

    # ── Joint angle validation ──────────────────────────────────────────────

    @staticmethod
    def check_joints(
        q: List[float],
        label: str = "q",
        allow_out_of_limits: bool = False,
    ) -> Tuple[List[float], Optional[str]]:
        """Validate a 7-element joint angle vector.

        Returns (cleaned_q, error_message). error_message is None if valid.
        """
        if not isinstance(q, (list, tuple)):
            return list(q) if hasattr(q, "__iter__") else ([], f"{label} 必须是列表")
        if len(q) != N_JOINTS:
            return (list(q), f"{label} 必须是 {N_JOINTS} 个元素的列表，收到 {len(q)} 个")
        cleaned = []
        for i, val in enumerate(q):
            try:
                v = float(val)
            except (TypeError, ValueError):
                return (list(q), f"{label}[{i}] 不是有效数值: {val!r}")
            if not math.isfinite(v):
                return (list(q), f"{label}[{i}] 不是有限数值: {v}")
            if not allow_out_of_limits:
                lo, hi = JOINT_LIMITS[i]
                if v < lo - 0.1 or v > hi + 0.1:
                    return (list(q), f"{label}[{i}]={v:.3f} 超出关节限位 [{lo:.3f}, {hi:.3f}]")
            cleaned.append(v)
        return (cleaned, None)

    @staticmethod
    def check_joint_path(
        q_path: List[List[float]],
        label: str = "q_path",
    ) -> Tuple[List[List[float]], Optional[str]]:
        """Validate a path of joint configurations."""
        if not isinstance(q_path, (list, tuple)):
            return ([], f"{label} 必须是列表")
        if len(q_path) == 0:
            return ([], f"{label} 不能为空")
        cleaned_path = []
        for idx, q in enumerate(q_path):
            clean_q, err = SafetyGate.check_joints(q, f"{label}[{idx}]")
            if err:
                return ([], err)
            cleaned_path.append(clean_q)
        return (cleaned_path, None)

    # ── Speed validation ────────────────────────────────────────────────────

    @staticmethod
    def check_speed(speed: float) -> Tuple[float, Optional[str]]:
        try:
            v = float(speed)
        except (TypeError, ValueError):
            return (0.0, f"speed 必须是数值，收到: {speed!r}")
        if not math.isfinite(v) or v <= 0:
            return (0.0, f"speed 必须 > 0，收到: {v}")
        if v > MAX_SPEED:
            return (MAX_SPEED, f"speed={v} 超过上限，已钳制到 {MAX_SPEED}")
        return (v, None)

    @staticmethod
    def check_duration(duration_s: float) -> Tuple[float, Optional[str]]:
        try:
            v = float(duration_s)
        except (TypeError, ValueError):
            return (0.0, f"duration_s 必须是数值，收到: {duration_s!r}")
        if not math.isfinite(v) or v <= 0:
            return (0.0, f"duration_s 必须 > 0，收到: {v}")
        if v > MAX_DURATION_S:
            return (MAX_DURATION_S, f"duration_s={v} 超过上限 {MAX_DURATION_S}s，已钳制")
        return (v, None)

    @staticmethod
    def check_settle(settle_s: float) -> Tuple[float, Optional[str]]:
        try:
            v = float(settle_s)
        except (TypeError, ValueError):
            return (1.0, f"settle_s 必须是数值，收到: {settle_s!r}")
        if not math.isfinite(v) or v < 0:
            return (1.0, f"settle_s 必须 >= 0，收到: {v}")
        if v > MAX_SETTLE_S:
            return (MAX_SETTLE_S, f"settle_s={v} 超过上限 {MAX_SETTLE_S}s，已钳制")
        return (v, None)

    # ── Pose validation ─────────────────────────────────────────────────────

    @staticmethod
    def check_position(pos: List[float]) -> Tuple[List[float], Optional[str]]:
        if not isinstance(pos, (list, tuple)) or len(pos) != 3:
            return ([], f"position 必须是 3 元素列表 [x, y, z]，收到: {pos!r}")
        cleaned = []
        for i, val in enumerate(pos):
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ([], f"position[{i}] 不是有效数值: {val!r}")
            if not math.isfinite(v):
                return ([], f"position[{i}] 不是有限数值: {v}")
            cleaned.append(v)
        return (cleaned, None)

    @staticmethod
    def check_rotation(R: List[List[float]]) -> Tuple[List[List[float]], Optional[str]]:
        if not isinstance(R, (list, tuple)) or len(R) != 3:
            return ([], f"rotation 必须是 3x3 矩阵，收到: {R!r}")
        cleaned = []
        for i, row in enumerate(R):
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                return ([], f"rotation[{i}] 必须是 3 元素列表，收到: {row!r}")
            clean_row = []
            for j, val in enumerate(row):
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    return ([], f"rotation[{i}][{j}] 不是有效数值: {val!r}")
                if not math.isfinite(v):
                    return ([], f"rotation[{i}][{j}] 不是有限数值: {v}")
                clean_row.append(v)
            cleaned.append(clean_row)
        return (cleaned, None)

    @staticmethod
    def check_pose(pose: Any) -> Tuple[Any, Optional[str]]:
        """Validate a pose as [position, rotation]."""
        if not isinstance(pose, (list, tuple)) or len(pose) != 2:
            return (None, f"pose 必须是 [position, rotation] 格式，收到: {pose!r}")
        pos, err = SafetyGate.check_position(pose[0])
        if err:
            return (None, f"pose.position: {err}")
        rot, err = SafetyGate.check_rotation(pose[1])
        if err:
            return (None, f"pose.rotation: {err}")
        return ([pos, rot], None)

    # ── Payload validation ──────────────────────────────────────────────────

    @staticmethod
    def check_payload(mass: float, com: List[float]) -> Tuple[float, List[float], Optional[str]]:
        try:
            m = float(mass)
        except (TypeError, ValueError):
            return (0.0, [], f"payload mass 必须是数值，收到: {mass!r}")
        if not math.isfinite(m) or m < MIN_PAYLOAD_MASS or m > MAX_PAYLOAD_MASS:
            return (0.0, [], f"payload mass={m} 超出范围 [{MIN_PAYLOAD_MASS}, {MAX_PAYLOAD_MASS}]")
        com_clean, err = SafetyGate.check_position(com)
        if err:
            return (0.0, [], f"payload com: {err}")
        return (m, com_clean, None)

    # ── Device validation ───────────────────────────────────────────────────

    @staticmethod
    def check_gripper_width(width: float) -> Tuple[float, Optional[str]]:
        try:
            w = float(width)
        except (TypeError, ValueError):
            return (0.0, f"gripper width 必须是数值，收到: {width!r}")
        if not math.isfinite(w) or w < GRIPPER_WIDTH_RANGE[0] or w > GRIPPER_WIDTH_RANGE[1]:
            return (0.0, f"gripper width={w} 超出范围 {GRIPPER_WIDTH_RANGE}")
        return (w, None)

    @staticmethod
    def check_hand_force(force: float) -> Tuple[float, Optional[str]]:
        try:
            f = float(force)
        except (TypeError, ValueError):
            return (0.0, f"hand force 必须是数值，收到: {force!r}")
        if not math.isfinite(f) or f < HAND_FORCE_RANGE[0] or f > HAND_FORCE_RANGE[1]:
            return (0.0, f"hand force={f} 超出范围 {HAND_FORCE_RANGE}")
        return (f, None)

    @staticmethod
    def check_gesture(gesture: str) -> Tuple[str, Optional[str]]:
        g = str(gesture).strip().lower()
        if g not in KNOWN_GESTURES:
            return (g, f"未知手势: {g!r}，已知手势: {sorted(KNOWN_GESTURES)}")
        return (g, None)

    @staticmethod
    def check_teleop_mode(mode: str) -> Tuple[str, Optional[str]]:
        m = str(mode).strip().lower()
        if m not in TELEOP_MODES:
            return (m, f"unknown teleop mode: {m!r}, expected: {sorted(TELEOP_MODES)}")
        return (m, None)

    # ── Gain validation ─────────────────────────────────────────────────────

    @staticmethod
    def check_gains(kp: Any, kd: Any) -> Tuple[Any, Any, Optional[str]]:
        """Validate gain arrays (list of 7 floats or scalar)."""
        for label, val in [("kp", kp), ("kd", kd)]:
            if val is None:
                continue
            if isinstance(val, (int, float)):
                if not math.isfinite(float(val)):
                    return (None, None, f"{label}={val} 不是有限数值")
            elif isinstance(val, (list, tuple)):
                if len(val) != N_JOINTS:
                    return (None, None, f"{label} 必须是 {N_JOINTS} 个元素或标量，收到 {len(val)} 个")
                for i, v in enumerate(val):
                    try:
                        fv = float(v)
                    except (TypeError, ValueError):
                        return (None, None, f"{label}[{i}] 不是有效数值: {v!r}")
                    if not math.isfinite(fv):
                        return (None, None, f"{label}[{i}] 不是有限数值: {fv}")
            else:
                return (None, None, f"{label} 必须是标量或列表，收到: {type(val).__name__}")
        return (kp, kd, None)

    # ── High-risk operation confirmation ────────────────────────────────────

    @staticmethod
    def check_high_risk(operation: str) -> str:
        """Return a warning string for high-risk operations.

        The LLM is expected to read this warning and confirm with the user.
        The tool itself does NOT block — litearm-server handles hard safety.
        """
        WARNINGS: Dict[str, str] = {
            "disable": (
                "⚠️ 高危操作: disable_motors 会使电机失能，机械臂在重力作用下坠落！"
                "请确认用户已明确要求此操作。"
            ),
            "restart": (
                "⚠️ 高危操作: restart_service 会重启控制服务，中断当前所有运动！"
                "请确认用户已明确要求此操作。"
            ),
            "direct_mit": (
                "⚠️ 高级操作: direct_mit_control 直接发送电机指令，绕过运动规划。"
                "参数错误可能导致机械臂剧烈运动。请确保参数正确。"
            ),
        }
        return WARNINGS.get(operation, "")