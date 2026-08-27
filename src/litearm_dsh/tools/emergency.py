"""emergency tools — safety-critical operations.

Tools: emergency_stop, clear_stop, enable_motors, disable_motors,
       clear_faults, reconnect_arm, restart_service
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..arm_handle import get_arm
from ..safety_gate import SafetyGate

gate = SafetyGate()


def emergency_stop() -> str:
    """急停：立即发送高优先级急停信号，独立通道，可随时安全停机。

    机械臂会立即停止运动并保持当前姿态。这是最安全的停止方式。
    调用后需 clear_stop 才能恢复正常运动。
    """
    try:
        arm = get_arm()
        arm.request_stop()
        return "🛑 急停已发送！机械臂已停止运动。调用 clear_stop 恢复。"
    except Exception as e:
        return f"emergency_stop 失败: {type(e).__name__}: {e}"


def clear_stop() -> str:
    """清除急停：解除急停状态，恢复正常运动能力。

    调用 emergency_stop 后，必须调用此工具才能恢复运动。
    """
    try:
        arm = get_arm()
        result = arm.clear_stop()
        return f"✅ 急停已清除: {result}"
    except Exception as e:
        return f"clear_stop 失败: {type(e).__name__}: {e}"


def enable_motors() -> str:
    """使能电机：上电并保持当前姿态。

    在 disable_motors 后调用此工具恢复电机使能。
    刚使能时会自动保持当前姿态。
    """
    try:
        arm = get_arm()
        arm.enable()
        return "✅ 电机已使能，保持当前姿态。"
    except Exception as e:
        return f"enable_motors 失败: {type(e).__name__}: {e}"


def disable_motors() -> str:
    """失能电机：关闭电机输出。

    ⚠️ 高危操作：电机失能后机械臂会在重力作用下坠落！
    请确认用户已明确要求此操作，且机械臂已处于安全位置或有人支撑。
    CAN 连接保持不断，可随时 re-enable。
    """
    risk = gate.check_high_risk("disable")
    try:
        arm = get_arm()
        arm.disable()
        return f"{risk}\n⚠️ 电机已失能！机械臂可能坠落。调用 enable_motors 恢复。"
    except Exception as e:
        return f"disable_motors 失败: {type(e).__name__}: {e}"


def clear_faults() -> str:
    """清除电机故障：清除所有电机的故障状态。

    返回已清除的故障列表 (motor_id, fault_code)。
    """
    try:
        arm = get_arm()
        cleared = arm.clear_faults()
        if cleared:
            return f"已清除故障: {cleared}"
        else:
            return "无故障需要清除。"
    except Exception as e:
        return f"clear_faults 失败: {type(e).__name__}: {e}"


def reconnect_arm() -> str:
    """重连硬件：从任何状态重新初始化电机连接。

    适用场景：机械臂热重启后、CAN 通信恢复后、从异常状态恢复。
    """
    try:
        arm = get_arm()
        result = arm.reconnect()
        return f"重连结果: {result}"
    except Exception as e:
        return f"reconnect_arm 失败: {type(e).__name__}: {e}"


def restart_service() -> str:
    """重启控制服务：请求 litearm-server 重启。

    ⚠️ 高危操作：会中断当前所有运动和控制！
    请确认用户已明确要求此操作。
    """
    risk = gate.check_high_risk("restart")
    try:
        arm = get_arm()
        result = arm.restart_service()
        return f"{risk}\n重启结果: {result}"
    except Exception as e:
        return f"restart_service 失败: {type(e).__name__}: {e}"


def get_guards() -> str:
    """读取当前护栏配置（slew_limit, tau_max, watchdog_timeout 等）。"""
    try:
        arm = get_arm()
        result = arm.get_guards()
        return f"护栏配置: {result}"
    except Exception as e:
        return f"get_guards 失败: {type(e).__name__}: {e}"


def set_guards(
    slew_limit: Any = None,
    tau_max: Any = None,
    watchdog_timeout: Any = None,
    position_bounds: Any = None,
    velocity_bounds: Any = None,
    jerk_limit: Any = None,
) -> str:
    """设置护栏参数（全局一次性配置）。

    ⚠️ 修改护栏可能影响安全保护！请确保理解每个参数的含义。

    Args:
        slew_limit: 斜率限制。
        tau_max: 最大力矩限制。
        watchdog_timeout: watchdog 超时（秒）。
        position_bounds: 位置边界。
        velocity_bounds: 速度边界。
        jerk_limit: 加加速度限制。
    """
    try:
        arm = get_arm()
        result = arm.set_guards(
            slew_limit=slew_limit,
            tau_max=tau_max,
            watchdog_timeout=watchdog_timeout,
            position_bounds=position_bounds,
            velocity_bounds=velocity_bounds,
            jerk_limit=jerk_limit,
        )
        return f"设置护栏: {result}"
    except Exception as e:
        return f"set_guards 失败: {type(e).__name__}: {e}"