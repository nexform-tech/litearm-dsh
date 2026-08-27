"""litearm-dsh: DeepSeek Harness plugin for LiteArm robotic arm control.

LLM-driven embodied AI — natural language → arm motion.
"""

__version__ = "0.1.0"

from .agent import LiteArmAgent, run_agent, run_cli
from .arm_handle import ArmHandle, get_arm, reset_arm
from .safety_gate import SafetyGate

__all__ = [
    "LiteArmAgent",
    "run_agent",
    "run_cli",
    "ArmHandle",
    "get_arm",
    "reset_arm",
    "SafetyGate",
    "__version__",
]