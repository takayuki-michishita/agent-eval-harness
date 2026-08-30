"""python examples/run_example.py で動く。外部APIは要らない。"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mock_agent import agent, reference

from agent_eval import (
    AbstentionGate,
    ExactMatch,
    Harness,
    SecondSystem,
    Task,
    ToolPolicy,
    render,
)

random.seed(7)

TASKS = [
    Task(id="読み取り-a", inputs={"key": "a"}, expected=12.0),
    Task(id="読み取り-b", inputs={"key": "b"}, expected=7.5),
    Task(id="読めない入力", inputs={"key": "zzz"}, should_abstain=True),
]

harness = Harness(
    graders=[
        ExactMatch(),
        SecondSystem(reference=reference),
        ToolPolicy(required=("lookup",), forbidden=("delete",)),
        AbstentionGate(),
    ],
    repeat=5,
)

print(render(harness.run(agent, TASKS)))
