"""record tools — trajectory recording, replay, and management.

Tools: record_trajectory, replay_trajectory, manage_trajectories
"""

from __future__ import annotations

from typing import Any, List, Optional

from ..arm_handle import get_arm


def record_trajectory(
    duration_s: Optional[float] = None,
    name: Optional[str] = None,
    sample_rate_hz: float = 100.0,
) -> str:
    """录制轨迹：进入零重力拖动模式，录制关节轨迹。

    调用后机械臂进入零重力，用户拖动机械臂。录制完成后自动退出零重力。

    Args:
        duration_s: 录制时长（秒），None 表示手动停止（需调用 stop_recording）。
        name: 轨迹名称（可选，用于后续回放识别）。
        sample_rate_hz: 采样率 Hz（默认 100）。
    """
    try:
        arm = get_arm()
        traj = arm.record_trajectory(
            duration_s=duration_s,
            name=name,
            sample_rate_hz=sample_rate_hz,
        )
        name_str = name or "unnamed"
        n_frames = len(traj.frames) if traj and traj.frames else 0
        dur = traj.duration_s if traj else 0
        return (
            f"轨迹录制完成: name={name_str}, "
            f"帧数={n_frames}, 时长={dur:.2f}s"
        )
    except Exception as e:
        return f"record_trajectory 失败: {type(e).__name__}: {e}"


def replay_trajectory(
    action: str,
    q_path: Optional[List[List[float]]] = None,
    trajectory_id: Optional[str] = None,
    speed: float = 1.0,
    goto_start: bool = True,
    goto_speed: float = 0.3,
) -> str:
    """回放轨迹：回放关节路径或已保存的轨迹。

    Args:
        action: "replay_path"（回放关节路径）或 "play_saved"（回放已保存轨迹）。
        q_path: 关节路径 [[q0..q6], ...]（action="replay_path" 时必填）。
        trajectory_id: 已保存轨迹的 ID（action="play_saved" 时必填）。
        speed: 回放速度比例 0.01~1.0（默认 1.0）。
        goto_start: 是否先移动到轨迹起点（默认 True）。
        goto_speed: 移动到起点的速度（默认 0.3）。
    """
    try:
        arm = get_arm()
        action = str(action).strip().lower()

        if action == "replay_path":
            if q_path is None:
                return "参数错误: action='replay_path' 需要 q_path 参数"
            if not isinstance(q_path, (list, tuple)) or len(q_path) == 0:
                return "参数错误: q_path 必须是非空路径"
            ok = arm.replay_joint_path(
                q_path, speed=speed,
                goto_start=goto_start, goto_speed=goto_speed,
            )
            return f"轨迹回放完成: {len(q_path)} 个航点, ok={ok}"

        elif action == "play_saved":
            if trajectory_id is None:
                return "参数错误: action='play_saved' 需要 trajectory_id 参数"
            ok = arm.play_trajectory(
                trajectory_id, speed=speed,
                goto_start=goto_start, goto_speed=goto_speed,
            )
            return f"已保存轨迹回放完成: id={trajectory_id}, ok={ok}"

        else:
            return f"未知操作: {action!r}。支持: replay_path, play_saved"

    except Exception as e:
        return f"replay_trajectory 失败: {type(e).__name__}: {e}"


def manage_trajectories(
    action: str,
    trajectory_id: Optional[str] = None,
    trajectory_name: Optional[str] = None,
    points: Optional[List[List[float]]] = None,
    duration: Optional[float] = None,
) -> str:
    """轨迹管理：列出/保存/删除轨迹。

    Args:
        action: "list"（列出所有轨迹）, "save"（保存轨迹）, "delete"（删除轨迹）。
        trajectory_id: 轨迹 ID（save/delete 时必填）。
        trajectory_name: 轨迹显示名称（save 时必填）。
        points: 关节路径点（save 时必填）。
        duration: 轨迹时长（save 时可选）。
    """
    try:
        arm = get_arm()
        action = str(action).strip().lower()

        if action == "list":
            result = arm.list_trajectories()
            return f"轨迹列表: {result}"

        elif action == "save":
            if trajectory_id is None:
                return "参数错误: action='save' 需要 trajectory_id"
            if trajectory_name is None:
                return "参数错误: action='save' 需要 trajectory_name"
            if points is None:
                return "参数错误: action='save' 需要 points"
            result = arm.save_trajectory(
                id=trajectory_id,
                name=trajectory_name,
                points=points,
                duration=duration,
            )
            return f"轨迹保存: id={trajectory_id}, name={trajectory_name} → {result}"

        elif action == "delete":
            if trajectory_id is None:
                return "参数错误: action='delete' 需要 trajectory_id"
            result = arm.delete_trajectory(trajectory_id)
            return f"轨迹删除: id={trajectory_id} → {result}"

        else:
            return f"未知操作: {action!r}。支持: list, save, delete"

    except Exception as e:
        return f"manage_trajectories 失败: {type(e).__name__}: {e}"


def start_recording() -> str:
    """开始录制轨迹（不进入零重力，在运动中录制）。"""
    try:
        arm = get_arm()
        result = arm.start_recording()
        return f"开始录制: {result}"
    except Exception as e:
        return f"start_recording 失败: {type(e).__name__}: {e}"


def stop_recording() -> str:
    """停止录制轨迹。"""
    try:
        arm = get_arm()
        result = arm.stop_recording()
        return f"停止录制: {result}"
    except Exception as e:
        return f"stop_recording 失败: {type(e).__name__}: {e}"


def discard_recording() -> str:
    """丢弃当前录制中的轨迹。"""
    try:
        arm = get_arm()
        result = arm.discard_recording()
        return f"丢弃录制: {result}"
    except Exception as e:
        return f"discard_recording 失败: {type(e).__name__}: {e}"


def get_recording_state() -> str:
    """查询当前录制状态。"""
    try:
        arm = get_arm()
        result = arm.get_recording_state()
        return f"录制状态: {result}"
    except Exception as e:
        return f"get_recording_state 失败: {type(e).__name__}: {e}"


def get_playback_state() -> str:
    """查询当前回放状态。"""
    try:
        arm = get_arm()
        result = arm.get_playback_state()
        return f"回放状态: {result}"
    except Exception as e:
        return f"get_playback_state 失败: {type(e).__name__}: {e}"