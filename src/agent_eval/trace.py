"""実行トレース。最終回答ではなく「何をしたか」を記録する。

2026年の評価は「答え合わせ」から行動監査へ移った。エージェントはツールを呼び、
状態を変え、複数ターンにまたがって働く。最終出力だけを見ても、
正しい答えに偶然たどり着いたのか、正しい手順を踏んだのかが区別できない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    """1回のツール呼び出し。"""

    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error: str | None = None
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.error is not None:
            self.ok = False


@dataclass
class Trace:
    """1回の実行の全記録。

    answer が None のとき、それは失敗ではなく **棄却** を意味しうる。
    abstained を見て区別すること。
    """

    task_id: str
    answer: Any = None
    steps: list[Step] = field(default_factory=list)
    abstained: bool = False
    abstain_reason: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def add(self, tool: str, **kw: Any) -> Step:
        step = Step(tool=tool, **kw)
        self.steps.append(step)
        return step

    def abstain(self, reason: str) -> None:
        """「読めない」「答えられない」を明示する。

        黙って推測を返すより、棄却するほうが本番では安全なことが多い。
        """
        self.abstained = True
        self.abstain_reason = reason
        self.answer = None

    @property
    def tool_calls(self) -> list[str]:
        return [s.tool for s in self.steps]

    @property
    def failed_steps(self) -> list[Step]:
        return [s for s in self.steps if not s.ok]

    @property
    def tool_error_rate(self) -> float:
        if not self.steps:
            return 0.0
        return len(self.failed_steps) / len(self.steps)
