"""ハーネス本体。同じ課題を N 回流し、トレース を採点して分布で見る。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .graders import Grader, Verdict
from .metrics import Summary, TaskResult
from .trace import Trace

AgentFn = Callable[["Task"], Trace]


@dataclass
class Task:
    """1件の評価課題。"""

    id: str
    inputs: dict[str, Any] = field(default_factory=dict)
    expected: Any = None
    should_abstain: bool = False


@dataclass
class Harness:
    """評価ハーネス。

    repeat を 1 にしない。非決定的な出力は 1 回では測れない。
    3〜5 回流して、合否が割れる課題を洗い出すのが目的。
    """

    graders: Sequence[Grader]
    repeat: int = 5

    def run(self, agent: AgentFn, tasks: Sequence[Task]) -> Summary:
        results: list[TaskResult] = []
        for task in tasks:
            traces: list[Trace] = []
            verdicts: list[list[Verdict]] = []
            for _ in range(self.repeat):
                trace = agent(task)
                trace.meta.setdefault("should_abstain", task.should_abstain)
                traces.append(trace)
                verdicts.append([g(trace, task.expected) for g in self.graders])
            results.append(TaskResult(task.id, traces, verdicts))
        return Summary(results)
