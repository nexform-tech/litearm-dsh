"""Tool registry — collects all tool functions from all groups.

Exports a single TOOLS dict for the DeepSeek Harness agent.
"""

from .move import (
    move_joints,
    move_linear,
    move_arc,
    move_waypoints,
    move_home,
    hold_position,
    zero_gravity,
    impedance_control,
    joint_follow,
    direct_mit_control,
)
from .query import (
    get_arm_state,
    get_tcp_pose,
    compute_fk,
    compute_ik,
    get_system_info,
    get_logs,
)
from .operate import (
    hand_control,
    gripper_control,
    teach_pendant,
    teleop_control,
)
from .record import (
    record_trajectory,
    replay_trajectory,
    manage_trajectories,
    start_recording,
    stop_recording,
    discard_recording,
    get_recording_state,
    get_playback_state,
)
from .configure import (
    set_arm_params,
    set_limits,
    set_end_effector,
    get_end_effector,
    manage_device,
)
from .emergency import (
    emergency_stop,
    clear_stop,
    enable_motors,
    disable_motors,
    clear_faults,
    reconnect_arm,
    restart_service,
    get_guards,
    set_guards,
)

# ── All tools exposed to the LLM ────────────────────────────────────────────────

TOOLS = {
    # Motion
    "move_joints": move_joints,
    "move_linear": move_linear,
    "move_arc": move_arc,
    "move_waypoints": move_waypoints,
    "move_home": move_home,
    "hold_position": hold_position,
    "zero_gravity": zero_gravity,
    "impedance_control": impedance_control,
    "joint_follow": joint_follow,
    "direct_mit_control": direct_mit_control,
    # Query
    "get_arm_state": get_arm_state,
    "get_tcp_pose": get_tcp_pose,
    "compute_fk": compute_fk,
    "compute_ik": compute_ik,
    "get_system_info": get_system_info,
    "get_logs": get_logs,
    # Operate
    "hand_control": hand_control,
    "gripper_control": gripper_control,
    "teach_pendant": teach_pendant,
    "teleop_control": teleop_control,
    # Record
    "record_trajectory": record_trajectory,
    "replay_trajectory": replay_trajectory,
    "manage_trajectories": manage_trajectories,
    "start_recording": start_recording,
    "stop_recording": stop_recording,
    "discard_recording": discard_recording,
    "get_recording_state": get_recording_state,
    "get_playback_state": get_playback_state,
    # Configure
    "set_arm_params": set_arm_params,
    "set_limits": set_limits,
    "set_end_effector": set_end_effector,
    "get_end_effector": get_end_effector,
    "manage_device": manage_device,
    # Emergency
    "emergency_stop": emergency_stop,
    "clear_stop": clear_stop,
    "enable_motors": enable_motors,
    "disable_motors": disable_motors,
    "clear_faults": clear_faults,
    "reconnect_arm": reconnect_arm,
    "restart_service": restart_service,
    "get_guards": get_guards,
    "set_guards": set_guards,
}

# ── Tool descriptions for the system prompt ─────────────────────────────────────

TOOL_CATEGORIES = {
    "运动控制": [
        "move_joints", "move_linear", "move_arc", "move_waypoints",
        "move_home", "hold_position", "zero_gravity",
        "impedance_control", "joint_follow", "direct_mit_control",
    ],
    "状态查询": [
        "get_arm_state", "get_tcp_pose", "compute_fk", "compute_ik",
        "get_system_info", "get_logs",
    ],
    "末端操作": [
        "hand_control", "gripper_control", "teach_pendant", "teleop_control",
    ],
    "轨迹": [
        "record_trajectory", "replay_trajectory", "manage_trajectories",
        "start_recording", "stop_recording", "discard_recording",
        "get_recording_state", "get_playback_state",
    ],
    "配置": [
        "set_arm_params", "set_limits", "set_end_effector",
        "get_end_effector", "manage_device",
    ],
    "安全": [
        "emergency_stop", "clear_stop", "enable_motors", "disable_motors",
        "clear_faults", "reconnect_arm", "restart_service",
        "get_guards", "set_guards",
    ],
}