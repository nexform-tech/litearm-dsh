"""move tools — motion control for LiteArm 7-DOF.

Tools: move_joints, move_linear, move_arc, move_waypoints, move_home,
       hold_position, zero_gravity, impedance_control, joint_follow,
       direct_mit_control
"""

from __future__ import annotations

from typing import Any, List, Optional

from ..arm_handle import get_arm
from ..safety_gate import SafetyGate

gate = SafetyGate()


# ── Basic motion ────────────────────────────────────────────────────────────────

def move_joints(
    q_target: List[float],
    speed: float = 0.5,
    settle_s: float = 1.0,
) -> str:
    """关节空间运动：将机械臂所有关节平滑移动到目标角度。

    这是最常用的运动指令。7 个关节独立规划 S 曲线，同时到达目标。
    适用场景：已知目标关节构型、需要快速可靠的运动。

    Args:
        q_target: 目标关节角 [J0, J1, J2, J3, J4, J5, J6]，单位弧度。
        speed: 速度比例 0.01~1.0（默认 0.5，安全保守）。
        settle_s: 到位后持位稳定时间（秒），默认 1.0。
    """
    q, err = gate.check_joints(q_target)
    if err:
        return f"参数错误: {err}"
    spd, warn = gate.check_speed(speed)
    prefix = f"⚠️ {warn}\n" if warn else ""
    stl, _ = gate.check_settle(settle_s)
    try:
        arm = get_arm()
        ok = arm.movej(q, speed=spd, settle_s=stl)
        return f"{prefix}move_joints 完成: q_target={[f'{v:.3f}' for v in q]}, speed={spd}, ok={ok}"
    except Exception as e:
        return f"move_joints 失败: {type(e).__name__}: {e}"


def move_linear(
    pose_goal: Any,
    speed: float = 0.5,
    settle_s: float = 0.8,
) -> str:
    """笛卡尔直线运动：末端在空间中直线移动到目标位姿。

    适用场景：需要末端走直线（如插拔、画线、精确放置）。

    Args:
        pose_goal: 目标位姿 [[px, py, pz], [[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]]]
        speed: 速度比例 0.01~1.0（默认 0.5）。
        settle_s: 到位后稳定时间（秒），默认 0.8。
    """
    pose, err = gate.check_pose(pose_goal)
    if err:
        return f"参数错误: {err}"
    spd, warn = gate.check_speed(speed)
    prefix = f"⚠️ {warn}\n" if warn else ""
    stl, _ = gate.check_settle(settle_s)
    try:
        arm = get_arm()
        ok = arm.movel(pose, speed=spd, settle_s=stl)
        return f"{prefix}move_linear 完成: ok={ok}"
    except Exception as e:
        return f"move_linear 失败: {type(e).__name__}: {e}"


def move_arc(
    pose_via: Any,
    pose_goal: Any,
    speed: float = 0.5,
    settle_s: float = 0.8,
) -> str:
    """笛卡尔圆弧运动：末端经过中间点走圆弧到达目标。

    Args:
        pose_via: 中间途经位姿（格式同 pose_goal）。
        pose_goal: 最终目标位姿。
        speed: 速度比例 0.01~1.0。
        settle_s: 到位后稳定时间（秒）。
    """
    via, err = gate.check_pose(pose_via)
    if err:
        return f"参数错误: pose_via: {err}"
    goal, err = gate.check_pose(pose_goal)
    if err:
        return f"参数错误: pose_goal: {err}"
    spd, warn = gate.check_speed(speed)
    prefix = f"⚠️ {warn}\n" if warn else ""
    stl, _ = gate.check_settle(settle_s)
    try:
        arm = get_arm()
        ok = arm.movec(via, goal, speed=spd, settle_s=stl)
        return f"{prefix}move_arc 完成: ok={ok}"
    except Exception as e:
        return f"move_arc 失败: {type(e).__name__}: {e}"


def move_waypoints(
    poses_goal: List[Any],
    speed: float = 0.5,
    settle_s: float = 0.8,
) -> str:
    """多航点运动：末端依次经过多个位姿航点，带转角平滑过渡。

    Args:
        poses_goal: 位姿列表，每个元素为 [position, rotation]。
        speed: 速度比例 0.01~1.0。
        settle_s: 到位后稳定时间（秒）。
    """
    if not isinstance(poses_goal, (list, tuple)) or len(poses_goal) == 0:
        return "参数错误: poses_goal 必须是非空列表"
    cleaned = []
    for i, pose in enumerate(poses_goal):
        cp, err = gate.check_pose(pose)
        if err:
            return f"参数错误: poses_goal[{i}]: {err}"
        cleaned.append(cp)
    spd, warn = gate.check_speed(speed)
    prefix = f"⚠️ {warn}\n" if warn else ""
    stl, _ = gate.check_settle(settle_s)
    try:
        arm = get_arm()
        ok = arm.movep(cleaned, speed=spd, settle_s=stl)
        return f"{prefix}move_waypoints 完成: {len(cleaned)} 个航点, ok={ok}"
    except Exception as e:
        return f"move_waypoints 失败: {type(e).__name__}: {e}"


def move_home(speed: float = 0.3, settle_s: float = 0.5) -> str:
    """回零：所有关节归零位，绕开限位和自碰撞检查。

    ⚠️ 前提：机械臂已处于安全构型，回零路径无障碍物。

    Args:
        speed: 速度比例 0.01~1.0（默认 0.3，保守）。
        settle_s: 到位后稳定时间（秒）。
    """
    spd, warn = gate.check_speed(speed)
    prefix = f"⚠️ {warn}\n" if warn else ""
    stl, _ = gate.check_settle(settle_s)
    try:
        arm = get_arm()
        ok = arm.home(speed=spd, settle_s=stl)
        return f"{prefix}move_home 完成: ok={ok}"
    except Exception as e:
        return f"move_home 失败: {type(e).__name__}: {e}"


def hold_position(kp_scale: float = 3.0) -> str:
    """原地保持：增大刚度维持当前位置。

    用于暂停运动、保持姿态等待下一步指令。

    Args:
        kp_scale: 刚度放大倍数（默认 3.0，越大保持越硬）。
    """
    try:
        fkp = float(kp_scale)
    except (TypeError, ValueError):
        return f"参数错误: kp_scale 必须是数值，收到: {kp_scale!r}"
    try:
        arm = get_arm()
        ok = arm.hold(kp_scale=fkp)
        return f"hold_position 完成: kp_scale={fkp}, ok={ok}"
    except Exception as e:
        return f"hold_position 失败: {type(e).__name__}: {e}"


# ── Advanced control ────────────────────────────────────────────────────────────

def zero_gravity(duration_s: float = 10.0) -> str:
    """零重力模式：电机仅补偿重力，机械臂可自由拖动。

    用于示教/拖动录制轨迹。到期自动退出或调用 hold_position 提前退出。

    Args:
        duration_s: 持续时间（秒），默认 10，最大 300。
    """
    dur, warn = gate.check_duration(duration_s)
    prefix = f"⚠️ {warn}\n" if warn else ""
    try:
        arm = get_arm()
        ok = arm.zero_gravity(duration_s=dur)
        return f"{prefix}zero_gravity 完成: duration_s={dur}, ok={ok}"
    except Exception as e:
        return f"zero_gravity 失败: {type(e).__name__}: {e}"


def impedance_control(
    q_des: List[float],
    K: Any,
    B: Any,
    mode: str = "joint",
    engage_sec: float = 0.3,
) -> str:
    """阻抗控制：使机械臂表现为弹簧-阻尼系统，可柔顺交互。

    Args:
        q_des: 期望关节角（关节模式）或期望位姿对应的关节角（笛卡尔模式）。
        K: 刚度系数，7 元素列表或标量。
        B: 阻尼系数，7 元素列表或标量。
        mode: "joint"（关节空间）或 "cartesian"（笛卡尔空间）。
        engage_sec: 渐进接合时间（秒），默认 0.3。
    """
    q, err = gate.check_joints(q_des)
    if err:
        return f"参数错误: q_des: {err}"
    _, _, err = gate.check_gains(K, B)
    if err:
        return f"参数错误: {err}"
    if mode not in ("joint", "cartesian"):
        return f"参数错误: mode 必须是 'joint' 或 'cartesian', 收到: {mode!r}"
    try:
        arm = get_arm()
        if mode == "joint":
            ok = arm.joint_impedance(q, K=K, B=B, engage_sec=engage_sec)
        else:
            ok = arm.cartesian_impedance(q, K_cart=K, B_cart=B, engage_sec=engage_sec)
        return f"impedance_control ({mode}) 完成: ok={ok}"
    except Exception as e:
        return f"impedance_control 失败: {type(e).__name__}: {e}"


def joint_follow(
    duration_s: float = 10.0,
    speed_limit: Any = None,
    engage_sec: float = 0.3,
) -> str:
    """关节跟随模式：机械臂以低刚度跟随外部目标（需 server 端 target_provider）。

    注意：此工具仅启动跟随模式，实际目标由 server 端目标提供者驱动。

    Args:
        duration_s: 持续时间（秒），默认 10，最大 300。
        speed_limit: 可选速度限制（7 元素列表或标量）。
        engage_sec: 渐进接合时间（秒）。
    """
    dur, warn = gate.check_duration(duration_s)
    prefix = f"⚠️ {warn}\n" if warn else ""
    try:
        arm = get_arm()
        ok = arm.joint_follow(duration_s=dur, speed_limit=speed_limit, engage_sec=engage_sec)
        return f"{prefix}joint_follow 完成: duration_s={dur}, ok={ok}"
    except Exception as e:
        return f"joint_follow 失败: {type(e).__name__}: {e}"


def direct_mit_control(
    kp: Any,
    kd: Any,
    q_ref: List[float],
    dq_ref: Optional[List[float]] = None,
    tau_ff: Optional[List[float]] = None,
) -> str:
    """直接 MIT 控制：发送单帧电机控制指令（kp, kd, q_ref, dq_ref, tau_ff）。

    ⚠️ 高危操作：绕过运动规划，直接控制电机。参数错误可能导致剧烈运动。
    首次调用后 server 自动进入 DIRECT 模式。需用户自行循环发送帧。

    Args:
        kp: 比例增益，7 元素列表。
        kd: 微分增益，7 元素列表。
        q_ref: 参考关节角，7 元素列表。
        dq_ref: 参考关节速度，7 元素列表（默认全零）。
        tau_ff: 前馈力矩，7 元素列表（默认全零）。
    """
    risk = gate.check_high_risk("direct_mit")
    q, err = gate.check_joints(q_ref, label="q_ref", allow_out_of_limits=True)
    if err:
        return f"参数错误: {err}"
    if dq_ref is None:
        dq_ref = [0.0] * 7
    if tau_ff is None:
        tau_ff = [0.0] * 7
    try:
        arm = get_arm()
        arm.send_mit(kp=kp, kd=kd, q_ref=q, dq_ref=dq_ref, tau_ff=tau_ff)
        return f"{risk}\ndirect_mit_control 已发送: q_ref={[f'{v:.3f}' for v in q]}"
    except Exception as e:
        return f"direct_mit_control 失败: {type(e).__name__}: {e}"