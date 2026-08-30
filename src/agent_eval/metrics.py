"""指標。非決定的な出力を、単発ではなく分布で見る。"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .graders import Verdict
from .trace import Trace


@dataclass
class TaskResult:
    task_id: str
    traces: list[Trace]
    verdicts: list[list[Verdict]]

    @property
    def runs(self) -> int:
        return len(self.traces)

    @property
    def pass_rate(self) -> float:
        """全採点器を通った実行の割合。沈黙した採点器は合格に数えない。"""
        if not self.verdicts:
            return 0.0
        ok = sum(1 for vs in self.verdicts if all(v.passed for v in vs if v.covered))
        return ok / len(self.verdicts)

    @property
    def reproducible(self) -> bool:
        """同じ入力を N 回流して、判定が割れなかったか。

        1回だけ通ったものを「動いた」と呼ばないための指標。
        割れるなら、それは合格でも不合格でもなく **不安定**。
        """
        rate = self.pass_rate
        return rate in (0.0, 1.0)

    @property
    def tool_error_rate(self) -> float:
        rates = [t.tool_error_rate for t in self.traces]
        return statistics.fmean(rates) if rates else 0.0

    @property
    def abstain_rate(self) -> float:
        if not self.traces:
            return 0.0
        return sum(1 for t in self.traces if t.abstained) / len(self.traces)

    @property
    def silent_graders(self) -> set[str]:
        """一度も判定できなかった採点器。

        ここが空でないなら、その観点は **見ていない**。
        0件を「問題なし」と読まないための出口。
        """
        seen: dict[str, bool] = {}
        for vs in self.verdicts:
            for v in vs:
                seen[v.name] = seen.get(v.name, False) or v.covered
        return {n for n, covered in seen.items() if not covered}


@dataclass
class Summary:
    results: list[TaskResult]

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return statistics.fmean(r.pass_rate for r in self.results)

    @property
    def unstable(self) -> list[TaskResult]:
        """合否が実行ごとに割れた課題。本番でいちばん危ないのはここ。"""
        return [r for r in self.results if not r.reproducible]

    @property
    def silent_graders(self) -> set[str]:
        """全課題を通じて一度も判定できなかった採点器。

        課題ごとの沈黙は正常なことがある（正解が未定義の課題で
        完全一致が判定しないなど）。ここで拾うのは
        **その観点を最初から一度も見ていない**場合だけ。
        """
        covered: dict[str, bool] = {}
        for r in self.results:
            for vs in r.verdicts:
                for v in vs:
                    covered[v.name] = covered.get(v.name, False) or v.covered
        return {n for n, c in covered.items() if not c}

    @property
    def partially_silent(self) -> dict[str, list[str]]:
        """判定できた課題と、できなかった課題が混在する採点器。

        「その課題は見ていない」を、合格と取り違えないための出口。
        """
        out: dict[str, list[str]] = {}
        for r in self.results:
            for name in r.silent_graders:
                out.setdefault(name, []).append(r.task_id)
        return {k: v for k, v in out.items() if k not in self.silent_graders}

    @property
    def tool_error_rate(self) -> float:
        if not self.results:
            return 0.0
        return statistics.fmean(r.tool_error_rate for r in self.results)
