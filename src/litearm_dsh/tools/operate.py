"""operate tools — end-effector devices and teleoperation.

Tools: hand_control, gripper_control, teach_pendant, teleop_control
"""

from __future__ import annotations

from typing import Any, Optional

from ..arm_handle import get_arm
from ..safety_gate import SafetyGate

gate = SafetyGate()


def hand_control(
    action: str,
    gesture: Optional[str] = None,
    force: Optional[float] = None,
    pose: Optional[Any] = None,
    speed: Optional[Any] = None,
    torque: Optional[Any] = None,
) -> str:
    """灵巧手控制：开/合/手势/逐指运动/力控/速度/力矩。

    Args:
        action: 操作类型 — "open"(打开), "close"(关闭), "gesture"(手势),
                "finger_move"(逐指运动), "set_force"(抓取力), "set_speed"(指速),
                "set_torque"(指力矩), "get_state"(查询状态), "list_gestures"(列出支持手势),
                "clear_faults"(清除故障)。
        gesture: 手势名称（action="gesture" 时必填），如 "pinch", "fist", "point", "open"。
        force: 抓取力 0.0~1.0（action="set_force" 时必填）。
        pose: 各指角度列表（action="finger_move" 时必填）。
        speed: 各指速度列表（action="set_speed" 时必填）。
        torque: 各指力矩列表（action="set_torque" 时必填）。
    """
    try:
        arm = get_arm()
        hand = arm.device("hand_0")

        action = str(action).strip().lower()

        if action == "open":
            ok = hand.open()
            return f"灵巧手: 打开 → ok={ok}"

        elif action == "close":
            ok = hand.close()
            return f"灵巧手: 关闭 → ok={ok}"

        elif action == "gesture":
            if gesture is None:
                return "参数错误: action='gesture' 需要 gesture 参数"
            g, err = gate.check_gesture(gesture)
            if err:
                return f"参数错误: {err}"
            ok = hand.set_gesture(g)
            return f"灵巧手: 手势 '{g}' → ok={ok}"

        elif action == "finger_move":
            if pose is None:
                return "参数错误: action='finger_move' 需要 pose 参数"
            ok = hand.finger_move(pose)
            return f"灵巧手: 逐指运动 → ok={ok}"

        elif action == "set_force":
            if force is None:
                return "参数错误: action='set_force' 需要 force 参数"
            f, err = gate.check_hand_force(force)
            if err:
                return f"参数错误: {err}"
            ok = hand.set_force(f)
            return f"灵巧手: 抓取力 {f} → ok={ok}"

        elif action == "set_speed":
            if speed is None:
                return "参数错误: action='set_speed' 需要 speed 参数"
            ok = hand.set_speed(speed)
            return f"灵巧手: 设置速度 → ok={ok}"

        elif action == "set_torque":
            if torque is None:
                return "参数错误: action='set_torque' 需要 torque 参数"
            ok = hand.set_torque(torque)
            return f"灵巧手: 设置力矩 → ok={ok}"

        elif action == "get_state":
            state = hand.get_state()
            return f"灵巧手状态: {state}"

        elif action == "list_gestures":
            gestures = hand.list_gestures()
            return f"支持的手势: {gestures}"

        elif action == "clear_faults":
            ok = hand.clear_faults()
            return f"灵巧手: 清除故障 → ok={ok}"

        else:
            return (
                f"未知操作: {action!r}。支持的操作: "
                "open, close, gesture, finger_move, set_force, set_speed, set_torque, "
                "get_state, list_gestures, clear_faults"
            )
    except Exception as e:
        return f"hand_control 失败: {type(e).__name__}: {e}"


def gripper_control(
    action: str,
    width: Optional[float] = None,
    force: Optional[float] = None,
) -> str:
    """夹爪控制：设置宽度、查询宽度、打开、关闭。

    Args:
        action: 操作类型 — "set_width"(设置宽度), "get_width"(查询宽度),
                "open"(打开=width=1.0), "close"(关闭=width=0.0)。
        width: 目标宽度 0.0~1.0（action="set_width" 时必填，0=全关，1=全开）。
        force: 抓取力 0.0~1.0。
    """
    try:
        arm = get_arm()
        gripper = arm.device("gripper_0")

        action = str(action).strip().lower()

        if action == "set_width":
            if width is None:
                return "参数错误: action='set_width' 需要 width 参数"
            w, err = gate.check_gripper_width(width)
            if err:
                return f"参数错误: {err}"
            ok = gripper.set_width(w)
            if force is not None:
                f, err = gate.check_hand_force(force)
                if err:
                    return f"夹爪宽度已设置={w}, 但 force 参数错误: {err}"
                gripper.set_force(f)
            return f"夹爪: 宽度 {w} → ok={ok}"

        elif action == "get_width":
            w = gripper.get_width()
            return f"夹爪当前宽度: {w}"

        elif action == "open":
            ok = gripper.open()
            return f"夹爪: 打开 → ok={ok}"

        elif action == "close":
            ok = gripper.close()
            return f"夹爪: 关闭 → ok={ok}"

        else:
            return f"未知操作: {action!r}。支持的操作: set_width, get_width, open, close"

    except Exception as e:
        return f"gripper_control 失败: {type(e).__name__}: {e}"


def teach_pendant(action: str = "get_joints") -> str:
    """示教板读取：获取关节角或按钮状态。

    Args:
        action: "get_joints"（读取关节角）或 "get_buttons"（读取按钮状态）。
    """
    try:
        arm = get_arm()
        teach = arm.device("teach_0")

        action = str(action).strip().lower()

        if action == "get_joints":
            joints = teach.get_joints()
            return f"示教板关节角: {joints}"
        elif action == "get_buttons":
            buttons = teach.get_buttons()
            return f"示教板按钮: {buttons}"
        else:
            return f"未知操作: {action!r}。支持: get_joints, get_buttons"
    except Exception as e:
        return f"teach_pendant 失败: {type(e).__name__}: {e}"


def teleop_control(
    action: str,
    mode: Optional[str] = None,
    peer: Optional[str] = None,
) -> str:
    """遥操控制：进入/退出/查询遥操状态。

    主臂（master）进入零重力，从臂（slave）跟随主臂运动。
    遥操期间 server 拒绝手动控制类 RPC。

    Args:
        action: "enter"（进入遥操）, "exit"（退出遥操）, "status"（查询状态）。
        mode: "master"（本臂作为主臂）或 "slave"（本臂作为从臂）。
        peer: 主臂网络端点（action="enter" mode="slave" 时必填），
              如 "tcp/10.0.0.2:7447"。
    """
    try:
        arm = get_arm()
        action = str(action).strip().lower()

        if action == "enter":
            if mode is None:
                return "参数错误: action='enter' 需要 mode 参数 ('master' 或 'slave')"
            m, err = gate.check_teleop_mode(mode)
            if err:
                return f"参数错误: {err}"
            params = {}
            if m == "slave":
                if peer is None:
                    return "参数错误: slave 模式需要 peer 参数（主臂网络端点）"
                params["peer"] = peer
            result = arm.enter_teleop(m, **params)
            return f"遥操: 进入 {m} 模式 → {result}"

        elif action == "exit":
            result = arm.exit_teleop()
            return f"遥操: 退出 → {result}"

        elif action == "status":
            status = arm.get_teleop_status()
            return f"遥操状态: {status}"

        else:
            return f"未知操作: {action!r}。支持: enter, exit, status"

    except Exception as e:
        return f"teleop_control 失败: {type(e).__name__}: {e}"