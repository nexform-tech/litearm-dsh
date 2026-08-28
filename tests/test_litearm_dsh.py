"""Tests for litearm_dsh — safety gate, tool registry, arm handle.

These tests do NOT require a real arm or litearm-server.
"""

from __future__ import annotations

import pytest

from litearm_dsh.safety_gate import SafetyGate


class TestSafetyGate:
    """Test the parameter validation gate."""

    def test_check_joints_valid(self):
        q = [0.0, 0.5, 0.0, -1.0, 0.0, 0.6, 0.0]
        cleaned, err = SafetyGate.check_joints(q)
        assert err is None
        assert len(cleaned) == 7
        assert cleaned == [float(v) for v in q]

    def test_check_joints_wrong_length(self):
        q = [0.0, 0.5, 0.0]
        cleaned, err = SafetyGate.check_joints(q)
        assert err is not None
        assert "7 个元素" in err

    def test_check_joints_out_of_limits(self):
        q = [0.0, 0.5, 0.0, -1.0, 0.0, 0.6, 99.0]  # J6 way out
        cleaned, err = SafetyGate.check_joints(q)
        assert err is not None
        assert "超出关节限位" in err

    def test_check_joints_allow_out_of_limits(self):
        q = [0.0, 0.5, 0.0, -1.0, 0.0, 0.6, 99.0]
        cleaned, err = SafetyGate.check_joints(q, allow_out_of_limits=True)
        assert err is None
        assert cleaned[6] == 99.0

    def test_check_joints_nan(self):
        q = [0.0, 0.5, 0.0, float("nan"), 0.0, 0.6, 0.0]
        cleaned, err = SafetyGate.check_joints(q)
        assert err is not None
        assert "不是有限数值" in err

    def test_check_speed_valid(self):
        v, err = SafetyGate.check_speed(0.5)
        assert err is None
        assert v == 0.5

    def test_check_speed_too_high(self):
        v, err = SafetyGate.check_speed(5.0)
        assert err is not None
        assert v == 2.0  # clamped to MAX_SPEED

    def test_check_speed_negative(self):
        v, err = SafetyGate.check_speed(-0.5)
        assert err is not None
        assert "必须 > 0" in err

    def test_check_position_valid(self):
        pos = [0.1, 0.2, 0.3]
        cleaned, err = SafetyGate.check_position(pos)
        assert err is None
        assert cleaned == [0.1, 0.2, 0.3]

    def test_check_position_wrong_length(self):
        pos = [0.1, 0.2]
        cleaned, err = SafetyGate.check_position(pos)
        assert err is not None
        assert "3 元素" in err

    def test_check_rotation_valid(self):
        R = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        cleaned, err = SafetyGate.check_rotation(R)
        assert err is None
        assert len(cleaned) == 3

    def test_check_pose_valid(self):
        pose = [[0.1, 0.2, 0.3], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]]
        cleaned, err = SafetyGate.check_pose(pose)
        assert err is None

    def test_check_payload_valid(self):
        mass, com, err = SafetyGate.check_payload(1.5, [0.0, 0.0, 0.05])
        assert err is None
        assert mass == 1.5

    def test_check_payload_too_heavy(self):
        mass, com, err = SafetyGate.check_payload(999.0, [0.0, 0.0, 0.0])
        assert err is not None
        assert "超出范围" in err

    def test_check_gesture_valid(self):
        g, err = SafetyGate.check_gesture("pinch")
        assert err is None
        assert g == "pinch"

    def test_check_gesture_unknown(self):
        g, err = SafetyGate.check_gesture("flying_kick")
        assert err is not None
        assert "未知手势" in err

    def test_check_teleop_mode_valid(self):
        m, err = SafetyGate.check_teleop_mode("master")
        assert err is None

    def test_check_teleop_mode_invalid(self):
        m, err = SafetyGate.check_teleop_mode("commander")
        assert err is not None

    def test_check_high_risk_disable(self):
        msg = SafetyGate.check_high_risk("disable")
        assert "高危" in msg
        assert "坠落" in msg

    def test_check_high_risk_restart(self):
        msg = SafetyGate.check_high_risk("restart")
        assert "高危" in msg
        assert "中断" in msg

    def test_check_gripper_width_valid(self):
        w, err = SafetyGate.check_gripper_width(0.5)
        assert err is None
        assert w == 0.5

    def test_check_gripper_width_out_of_range(self):
        w, err = SafetyGate.check_gripper_width(1.5)
        assert err is not None

    def test_check_hand_force_valid(self):
        f, err = SafetyGate.check_hand_force(0.3)
        assert err is None

    def test_check_hand_force_out_of_range(self):
        f, err = SafetyGate.check_hand_force(1.5)
        assert err is not None

    def test_check_duration_too_long(self):
        d, err = SafetyGate.check_duration(999.0)
        assert err is not None
        assert d == 300.0  # clamped

    def test_check_settle_valid(self):
        s, err = SafetyGate.check_settle(0.5)
        assert err is None

    def test_check_settle_negative(self):
        s, err = SafetyGate.check_settle(-1.0)
        assert err is not None

    def test_check_gains_valid_list(self):
        kp = [1.0] * 7
        kd = [0.1] * 7
        kp2, kd2, err = SafetyGate.check_gains(kp, kd)
        assert err is None

    def test_check_gains_wrong_length(self):
        kp = [1.0, 2.0, 3.0]
        kd = [0.1] * 7
        kp2, kd2, err = SafetyGate.check_gains(kp, kd)
        assert err is not None
        assert "7 个元素" in err

    def test_check_joint_path_valid(self):
        path = [[0.0] * 7, [0.1] * 7, [0.2] * 7]
        cleaned, err = SafetyGate.check_joint_path(path)
        assert err is None
        assert len(cleaned) == 3

    def test_check_joint_path_empty(self):
        cleaned, err = SafetyGate.check_joint_path([])
        assert err is not None
        assert "不能为空" in err


class TestToolRegistry:
    """Test that all tools are registered and callable."""

    def test_all_tools_registered(self):
        from litearm_dsh.tools import TOOLS, TOOL_CATEGORIES

        assert len(TOOLS) == 42
        # Check all categories are non-empty
        for cat, names in TOOL_CATEGORIES.items():
            assert len(names) > 0, f"Category {cat} is empty"
            for name in names:
                assert name in TOOLS, f"Tool {name} not in TOOLS"

    def test_tool_functions_are_callable(self):
        from litearm_dsh.tools import TOOLS

        for name, fn in TOOLS.items():
            assert callable(fn), f"Tool {name} is not callable"

    def test_no_duplicate_tools(self):
        from litearm_dsh.tools import TOOLS, TOOL_CATEGORIES

        # Check that each tool appears in exactly one category
        all_tools = []
        for names in TOOL_CATEGORIES.values():
            all_tools.extend(names)
        assert len(all_tools) == len(set(all_tools)), "Duplicate tools in categories"


class TestModuleImports:
    """Test that all modules can be imported without a real arm."""

    def test_import_core(self):
        import litearm_dsh
        assert litearm_dsh.__version__ == "0.1.0"

    def test_import_safety_gate(self):
        from litearm_dsh.safety_gate import SafetyGate
        assert SafetyGate is not None

    def test_import_tools(self):
        from litearm_dsh.tools import TOOLS
        assert len(TOOLS) > 0

    def test_import_tool_modules(self):
        from litearm_dsh.tools import move
        from litearm_dsh.tools import query
        from litearm_dsh.tools import operate
        from litearm_dsh.tools import record
        from litearm_dsh.tools import configure
        from litearm_dsh.tools import emergency
        assert all([move, query, operate, record, configure, emergency])