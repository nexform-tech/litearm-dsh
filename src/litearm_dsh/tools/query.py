"""query tools — state reading and kinematics.

Tools: get_arm_state, get_tcp_pose, compute_fk, compute_ik, get_system_info
"""

from __future__ import annotations

from typing import Any, List, Optional

from ..arm_handle import ArmHandle, get_arm
from ..safety_gate import SafetyGate

gate = SafetyGate()


def get_arm_state() -> str:
    """读取机械臂当前状态：关节角(q)、速度(dq)、力矩(tau)、故障、温度、watchdog。

    这是最常用的状态查询工具。返回完整的状态快照，用于了解机械臂当前状况。
    不产生运动，随时可安全调用。
    """
    return ArmHandle.get_state_summary()


def get_tcp_pose() -> str:
    """获取当前末端 TCP 位姿：位置 [x, y, z] 和 3x3 旋转矩阵。

    用于了解机械臂末端在空间中的精确位置和姿态。
    不产生运动，随时可安全调用。
    """
    try:
        arm = get_arm()
        pos, rot = arm.get_tcp_pose()
        return (
            f"TCP 位姿:\n"
            f"  位置: [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}]\n"
            f"  旋转矩阵:\n"
            f"    [{rot[0][0]:.4f}, {rot[0][1]:.4f}, {rot[0][2]:.4f}]\n"
            f"    [{rot[1][0]:.4f}, {rot[1][1]:.4f}, {rot[1][2]:.4f}]\n"
            f"    [{rot[2][0]:.4f}, {rot[2][1]:.4f}, {rot[2][2]:.4f}]"
        )
    except Exception as e:
        return f"get_tcp_pose 失败: {type(e).__name__}: {e}"


def compute_fk(q: List[float]) -> str:
    """正运动学计算：给定关节角，计算末端位姿（纯计算，不运动）。

    Args:
        q: 关节角 [J0..J6]，单位弧度。
    """
    qc, err = gate.check_joints(q, allow_out_of_limits=True)
    if err:
        return f"参数错误: {err}"
    try:
        arm = get_arm()
        pos, rot = arm.fk(qc)
        return (
            f"FK 结果:\n"
            f"  输入 q: {[f'{v:.3f}' for v in qc]}\n"
            f"  位置: [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}]\n"
            f"  旋转矩阵:\n"
            f"    [{rot[0][0]:.4f}, {rot[0][1]:.4f}, {rot[0][2]:.4f}]\n"
            f"    [{rot[1][0]:.4f}, {rot[1][1]:.4f}, {rot[1][2]:.4f}]\n"
            f"    [{rot[2][0]:.4f}, {rot[2][1]:.4f}, {rot[2][2]:.4f}]"
        )
    except Exception as e:
        return f"compute_fk 失败: {type(e).__name__}: {e}"


def compute_ik(
    pos_d: List[float],
    R_d: List[List[float]],
    q_seed: Optional[List[float]] = None,
) -> str:
    """逆运动学计算：给定目标位姿，求解关节角（纯计算，不运动）。

    Args:
        pos_d: 目标位置 [x, y, z]。
        R_d: 目标旋转矩阵 3x3。
        q_seed: 可选，初始猜测关节角（7 元素），用于确定解的分支。
    """
    pos, err = gate.check_position(pos_d)
    if err:
        return f"参数错误: pos_d: {err}"
    rot, err = gate.check_rotation(R_d)
    if err:
        return f"参数错误: R_d: {err}"
    if q_seed is not None:
        qs, err = gate.check_joints(q_seed, label="q_seed", allow_out_of_limits=True)
        if err:
            return f"参数错误: q_seed: {err}"
        q_seed = qs
    try:
        arm = get_arm()
        q, success = arm.ik(pos, rot, q_seed=q_seed)
        if success:
            return f"IK 成功: q={[f'{v:.4f}' for v in q]}"
        else:
            return f"IK 失败: 目标位姿不可达或超出工作空间"
    except Exception as e:
        return f"compute_ik 失败: {type(e).__name__}: {e}"


def get_system_info() -> str:
    """获取系统信息：CPU 使用率、内存、板温、运行时间。

    不产生运动，随时可安全调用。
    """
    try:
        arm = get_arm()
        stats = arm.get_system_stats()
        if not stats:
            return "系统信息: 无数据"
        lines = ["系统信息:"]
        for key, val in stats.items():
            lines.append(f"  {key}: {val}")
        return "\n".join(lines)
    except Exception as e:
        return f"get_system_info 失败: {type(e).__name__}: {e}"


def get_logs(page: int = 1, size: int = 50, search: str = "") -> str:
    """查询 server 端日志（分页）。

    Args:
        page: 页码（从 1 开始）。
        size: 每页条数（默认 50）。
        search: 搜索关键词（可选）。
    """
    try:
        arm = get_arm()
        result = arm.get_logs(page=page, size=size, search=search)
        if not result:
            return "日志: 无数据"
        logs = result.get("logs", result.get("data", []))
        total = result.get("total", len(logs))
        lines = [f"日志 (第 {page} 页, 共 {total} 条):"]
        for entry in logs[:20]:  # 限制返回量避免 token 爆炸
            lines.append(f"  {entry}")
        return "\n".join(lines)
    except Exception as e:
        return f"get_logs 失败: {type(e).__name__}: {e}"