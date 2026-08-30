"""外部APIなしで動く、わざと不安定なエージェント。

本物のエージェントを差し替えるのは agent() を置き換えるだけ。
Claude Agent SDK でも、自前のループでも、返すのが Trace なら何でもよい。
"""

from __future__ import annotations

import random

from agent_eval import Task, Trace

# 単位つきの数値を読み取る、という設定。読めない入力が混ざっている。
TABLE = {"a": 12.0, "b": 7.5, "c": 3.25}


def agent(task: Task) -> Trace:
    key = task.inputs["key"]
    trace = Trace(task_id=task.id)

    trace.add("lookup", args={"key": key})

    if key not in TABLE:
        # 読めないものは読めないと言う。推測を返さない。
        trace.abstain(f"未知のキー {key!r}")
        return trace

    # 5回に1回、ツールが落ちる（本番でよくある）
    if random.random() < 0.2:
        trace.add("parse", args={"key": key}, error="timeout")
        trace.answer = None
        return trace

    trace.add("parse", args={"key": key})

    # 10回に1回、単位を取り違える（見つけにくい種類の誤り）
    value = TABLE[key]
    if random.random() < 0.1:
        value = value * 1000

    trace.answer = value
    return trace


def reference(trace: Trace) -> float:
    """独立した第2系統。主系とは別の作りで同じ答えを出す。"""
    key = trace.steps[0].args["key"]
    return {"a": 12.0, "b": 7.5, "c": 3.25}[key]
