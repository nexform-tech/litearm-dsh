#!/usr/bin/env python3
"""litearm-dsh CLI — LLM-driven LiteArm robotic arm control.

Usage:
    python -m litearm_dsh
    python -m litearm_dsh --endpoint tcp/192.168.31.237:7447
    python -m litearm_dsh --model deepseek-reasoner

Environment:
    DEEPSEEK_API_KEY    DeepSeek API key (required)
    LITEARM_ENDPOINT    litearm-server endpoint (default tcp/127.0.0.1:7447)
"""

from __future__ import annotations

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="litearm-dsh: LLM-driven LiteArm robotic arm control",
    )
    parser.add_argument(
        "--endpoint", "-e",
        default=os.environ.get("LITEARM_ENDPOINT", "tcp/127.0.0.1:7447"),
        help="litearm-server zenoh endpoint (default: tcp/127.0.0.1:7447)",
    )
    parser.add_argument(
        "--arm-id",
        default="armA",
        help="Arm identifier (default: armA)",
    )
    parser.add_argument(
        "--model", "-m",
        default="deepseek-chat",
        help="DeepSeek model (default: deepseek-chat)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DEEPSEEK_API_KEY", ""),
        help="DeepSeek API key (default: env DEEPSEEK_API_KEY)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print tool call details",
    )
    parser.add_argument(
        "--prompt", "-p",
        default=None,
        help="Single prompt mode (non-interactive)",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("错误: 需要设置 DEEPSEEK_API_KEY 环境变量或通过 --api-key 传入", file=sys.stderr)
        sys.exit(1)

    # Set for litearm-python
    os.environ["LITEARM_ENDPOINT"] = args.endpoint

    from litearm_dsh.agent import LiteArmAgent

    agent = LiteArmAgent(
        endpoint=args.endpoint,
        arm_id=args.arm_id,
        model=args.model,
        api_key=args.api_key,
        verbose=args.verbose,
    )

    try:
        if args.prompt:
            result = agent.run(args.prompt)
            print(result)
        else:
            agent.cli()
    finally:
        agent.close()


if __name__ == "__main__":
    main()