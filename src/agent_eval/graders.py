"""採点器。1つの答えを複数の独立した観点で見る。

設計の要点は「機械の検査は下限であって上限ではない」こと。
0件は「問題なし」の証拠にならない。だから採点器は必ず
`verdict` に加えて `covered`（この採点器が実際に判定できたか）を返す。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .trace import Trace


@dataclass
class Verdict:
    """採点結果。

    passed  : 合格したか
    covered : この採点器が判定を下せたか。False なら「見ていない」であって
              「問題なし」ではない
    """

    name: str
    passed: bool
    covered: bool = True
    detail: str = ""
    score: float | None = None

    @property
    def silent(self) -> bool:
        """判定できなかった＝沈黙。合格と数えてはいけない。"""
        return not self.covered


class Grader(Protocol):
    name: str

    def __call__(self, trace: Trace, expected: Any) -> Verdict: ...


@dataclass
class ExactMatch:
    """決定的な採点。正解が一意に決まるときだけ使える。"""

    name: str = "exact_match"

    def __call__(self, trace: Trace, expected: Any) -> Verdict:
        if expected is None:
            return Verdict(self.name, False, covered=False, detail="正解が未定義")
        if trace.abstained:
            return Verdict(self.name, False, detail=f"棄却: {trace.abstain_reason}")
        ok = trace.answer == expected
        return Verdict(self.name, ok, detail=f"{trace.answer!r} vs {expected!r}")


@dataclass
class SecondSystem:
    """独立した第2系統との突き合わせ。

    同じ仕組みをもう一度動かしても、同じ間違いをするだけ。
    **別の作りの実装**に同じ入力を通し、食い違った箇所だけを人に上げる。

    出所は音声合成の読み誤り検出。VOICEVOX(OpenJTalk系)と UniDic の
    2系統で読みを出して突き合わせたところ、疑う理由が無かった語から
    誤読が出た。疑うかどうかと無関係に候補が挙がるのが要点。
    """

    reference: Callable[[Trace], Any]
    name: str = "second_system"
    equal: Callable[[Any, Any], bool] | None = None

    def __call__(self, trace: Trace, expected: Any) -> Verdict:
        if trace.abstained:
            return Verdict(self.name, True, detail="棄却は突き合わせの対象外")
        try:
            other = self.reference(trace)
        except Exception as exc:  # noqa: BLE001 -- 参照系の失敗で本体を止めない。
            # 何で落ちたかを問わず「判定できなかった」に倒すのが正しい。
            # ここを狭く捕まえると、想定外の例外で評価そのものが死ぬ。
            return Verdict(self.name, False, covered=False, detail=f"参照系が失敗: {exc}")
        eq = self.equal or (lambda a, b: a == b)
        ok = eq(trace.answer, other)
        return Verdict(self.name, ok, detail=f"主系 {trace.answer!r} / 参照系 {other!r}")


@dataclass
class ToolPolicy:
    """行動監査。最終回答ではなく、通った手順を見る。

    required : 必ず呼ばれているべきツール
    forbidden: 呼んではいけないツール（副作用のあるもの等）
    """

    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()
    max_tool_error_rate: float = 0.0
    name: str = "tool_policy"

    def __call__(self, trace: Trace, expected: Any) -> Verdict:
        called = set(trace.tool_calls)
        missing = [t for t in self.required if t not in called]
        used = [t for t in self.forbidden if t in called]
        rate = trace.tool_error_rate
        problems = []
        if missing:
            problems.append(f"未呼び出し {missing}")
        if used:
            problems.append(f"禁止ツール {used}")
        if rate > self.max_tool_error_rate:
            problems.append(f"ツール失敗率 {rate:.0%}")
        return Verdict(self.name, not problems, detail="; ".join(problems) or "問題なし")


@dataclass
class AbstentionGate:
    """棄却設計。答えられない入力で、黙って推測していないか。

    should_abstain が True の課題で答えを返したら不合格。
    「読めないものは読めないと言う」を評価に組み込む。
    """

    name: str = "abstention_gate"

    def __call__(self, trace: Trace, expected: Any) -> Verdict:
        want = bool(trace.meta.get("should_abstain", False))
        if not want:
            return Verdict(self.name, True, covered=False, detail="棄却を要求しない課題")
        if trace.abstained:
            return Verdict(self.name, True, detail=f"正しく棄却: {trace.abstain_reason}")
        return Verdict(self.name, False, detail=f"棄却すべき入力に {trace.answer!r} を返した")
