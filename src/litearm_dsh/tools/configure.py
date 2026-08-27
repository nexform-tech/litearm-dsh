"""configure tools — parameter tuning and device management.

Tools: set_arm_params, set_limits, set_end_effector, manage_device
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..arm_handle import get_arm
from ..safety_gate import SafetyGate

gate = SafetyGate()


def set_arm_params(
    action: str,
    kp: Any = None,
    kd: Any = None,
    mass: Optional[float] = None,
    com: Optional[List[float]] = None,
    base_rpy: Optional[List[float]] = None,
    gravity: Optional[List[float]] = None,
) -> str:
    """设置机械臂参数：PD 增益、末端负载、安装姿态。

    Args:
        action: "set_gains"（PD 增益）, "get_gains"（查询增益）,
                "set_payload"（末端负载）, "get_payload"（查询负载）,
                "set_installation"（安装姿态）, "get_installation"（查询安装姿态）。
        kp: 比例增益（set_gains 时），7 元素列表或标量。
        kd: 微分增益（set_gains 时），7 元素列表或标量。
        mass: 负载质量 kg（set_payload 时）。
        com: 负载质心 [x, y, z]（set_payload 时）。
        base_rpy: 安装姿态 [roll, pitch, yaw]（set_installation 时）。
        gravity: 重力向量 [gx, gy, gz]（set_installation 时）。
    """
    try:
        arm = get_arm()
        action = str(action).strip().lower()

        if action == "set_gains":
            _, _, err = gate.check_gains(kp, kd)
            if err:
                return f"参数错误: {err}"
            result = arm.set_gains(kp=kp, kd=kd)
            return f"设置增益: {result}"

        elif action == "get_gains":
            result = arm.get_gains()
            return f"当前增益: {result}"

        elif action == "set_payload":
            if mass is None or com is None:
                return "参数错误: action='set_payload' 需要 mass 和 com 参数"
            m, c, err = gate.check_payload(mass, com)
            if err:
                return f"参数错误: {err}"
            result = arm.set_payload(mass=m, com=tuple(c))
            return f"设置负载: mass={m}, com={c} → {result}"

        elif action == "get_payload":
            result = arm.get_payload()
            return f"当前负载: {result}"

        elif action == "set_installation":
            result = arm.set_installation(base_rpy=base_rpy, gravity=gravity)
            return f"设置安装: {result}"

        elif action == "get_installation":
            result = arm.get_installation()
            return f"当前安装: {result}"

        else:
            return (
                f"未知操作: {action!r}。支持: "
                "set_gains, get_gains, set_payload, get_payload, set_installation, get_installation"
            )

    except Exception as e:
        return f"set_arm_params 失败: {type(e).__name__}: {e}"


def set_limits(
    action: str,
    joint_limits: Optional[Dict[str, Any]] = None,
    cartesian_limits: Optional[Dict[str, Any]] = None,
    collision_config: Optional[Dict[str, Any]] = None,
    zero_offsets: Optional[Dict[str, Any]] = None,
) -> str:
    """设置机械臂限位与安全参数。

    Args:
        action: "get_joint_limits" / "set_joint_limits",
                "get_cartesian_limits" / "set_cartesian_limits",
                "get_collision_config" / "set_collision_config",
                "get_zero_offsets" / "set_zero_offsets"。
        joint_limits: 关节限位配置（set_joint_limits 时）。
        cartesian_limits: 笛卡尔限位配置（set_cartesian_limits 时）。
        collision_config: 碰撞检测配置（set_collision_config 时）。
        zero_offsets: 零位偏移配置（set_zero_offsets 时）。
    """
    try:
        arm = get_arm()
        action = str(action).strip().lower()

        if action == "get_joint_limits":
            return f"关节限位: {arm.get_joint_limits()}"
        elif action == "set_joint_limits":
            if joint_limits is None:
                return "参数错误: action='set_joint_limits' 需要 joint_limits 参数"
            return f"设置关节限位: {arm.set_joint_limits(joint_limits)}"
        elif action == "get_cartesian_limits":
            return f"笛卡尔限位: {arm.get_cartesian_limits()}"
        elif action == "set_cartesian_limits":
            if cartesian_limits is None:
                return "参数错误: action='set_cartesian_limits' 需要 cartesian_limits 参数"
            return f"设置笛卡尔限位: {arm.set_cartesian_limits(cartesian_limits)}"
        elif action == "get_collision_config":
            return f"碰撞配置: {arm.get_collision_config()}"
        elif action == "set_collision_config":
            if collision_config is None:
                return "参数错误: action='set_collision_config' 需要 collision_config 参数"
            return f"设置碰撞配置: {arm.set_collision_config(collision_config)}"
        elif action == "get_zero_offsets":
            return f"零位偏移: {arm.get_zero_offsets()}"
        elif action == "set_zero_offsets":
            if zero_offsets is None:
                return "参数错误: action='set_zero_offsets' 需要 zero_offsets 参数"
            return f"设置零位偏移: {arm.set_zero_offsets(zero_offsets)}"
        else:
            return (
                f"未知操作: {action!r}。支持: "
                "get/set_joint_limits, get/set_cartesian_limits, "
                "get/set_collision_config, get/set_zero_offsets"
            )
    except Exception as e:
        return f"set_limits 失败: {type(e).__name__}: {e}"


def set_end_effector(config: Dict[str, Any]) -> str:
    """设置末端执行器配置。

    Args:
        config: 末端执行器配置字典（如类型、安装偏移等）。
    """
    try:
        arm = get_arm()
        result = arm.set_end_effector(config)
        return f"设置末端执行器: {result}"
    except Exception as e:
        return f"set_end_effector 失败: {type(e).__name__}: {e}"


def get_end_effector() -> str:
    """查询末端执行器配置。"""
    try:
        arm = get_arm()
        result = arm.get_end_effector()
        return f"末端执行器: {result}"
    except Exception as e:
        return f"get_end_effector 失败: {type(e).__name__}: {e}"


def manage_device(
    action: str,
    category: Optional[str] = None,
    subtype: Optional[str] = None,
    device_id: str = "end_0",
    can_iface: str = "",
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """末端设备管理：连接/断开/查询设备。

    server 会按需 fork device_daemon 来管理末端设备。

    Args:
        action: "list_types"（列出可用设备类型）, "connect"（连接设备）,
                "disconnect"（断开设备）, "get_active"（查询当前设备）。
        category: 设备分类（connect 时），如 "hand", "gripper"。
        subtype: 设备子类型（connect 时），如 "lite6_hand"。
        device_id: 设备 ID（默认 "end_0"）。
        can_iface: CAN 接口名（connect 时，默认 ""）。
        config: 设备配置（connect 时可选）。
    """
    try:
        arm = get_arm()
        action = str(action).strip().lower()

        if action == "list_types":
            result = arm.list_device_types()
            return f"可用设备类型: {result}"

        elif action == "connect":
            if category is None or subtype is None:
                return "参数错误: action='connect' 需要 category 和 subtype 参数"
            result = arm.connect_device(
                category=category,
                subtype=subtype,
                device_id=device_id,
                can_iface=can_iface,
                config=config,
            )
            return f"连接设备: {category}/{subtype} → {result}"

        elif action == "disconnect":
            result = arm.disconnect_device(device_id)
            return f"断开设备: {device_id} → {result}"

        elif action == "get_active":
            result = arm.get_active_device(device_id)
            return f"当前设备: {result}"

        else:
            return f"未知操作: {action!r}。支持: list_types, connect, disconnect, get_active"

    except Exception as e:
        return f"manage_device 失败: {type(e).__name__}: {e}"