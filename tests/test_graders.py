from agent_eval import (
    AbstentionGate,
    ExactMatch,
    SecondSystem,
    ToolPolicy,
    Trace,
)


def make(answer=None, tools=(), abstained=False, errors=()):
    t = Trace(task_id="t")
    for i, name in enumerate(tools):
        t.add(name, error="boom" if i in errors else None)
    if abstained:
        t.abstain("読めない")
    else:
        t.answer = answer
    return t


class TestExactMatch:
    def test_合格(self):
        assert ExactMatch()(make(answer=1), 1).passed

    def test_不一致は不合格(self):
        assert not ExactMatch()(make(answer=2), 1).passed

    def test_正解が未定義なら判定しない(self):
        v = ExactMatch()(make(answer=1), None)
        assert not v.covered and v.silent

    def test_棄却は不合格として扱う(self):
        assert not ExactMatch()(make(abstained=True), 1).passed


class TestSecondSystem:
    def test_一致すれば合格(self):
        g = SecondSystem(reference=lambda tr: 42)
        assert g(make(answer=42), None).passed

    def test_食い違えば不合格(self):
        g = SecondSystem(reference=lambda tr: 42)
        assert not g(make(answer=41), None).passed

    def test_参照系が落ちたら判定しない(self):
        def boom(tr):
            raise RuntimeError("参照系が停止")

        v = SecondSystem(reference=boom)(make(answer=1), None)
        assert v.silent, "落ちた採点器を合格に数えてはいけない"

    def test_棄却は突き合わせの対象外(self):
        g = SecondSystem(reference=lambda tr: 42)
        assert g(make(abstained=True), None).passed


class TestToolPolicy:
    def test_必須ツールが無ければ不合格(self):
        assert not ToolPolicy(required=("lookup",))(make(tools=["parse"]), None).passed

    def test_禁止ツールを呼んだら不合格(self):
        g = ToolPolicy(forbidden=("delete",))
        assert not g(make(tools=["lookup", "delete"]), None).passed

    def test_ツール失敗率の上限(self):
        t = make(tools=["a", "b"], errors=(0,))
        assert not ToolPolicy(max_tool_error_rate=0.0)(t, None).passed
        assert ToolPolicy(max_tool_error_rate=0.5)(t, None).passed


class TestAbstentionGate:
    def test_棄却すべき入力で棄却したら合格(self):
        t = make(abstained=True)
        t.meta["should_abstain"] = True
        assert AbstentionGate()(t, None).passed

    def test_棄却すべき入力で答えたら不合格(self):
        t = make(answer=3)
        t.meta["should_abstain"] = True
        assert not AbstentionGate()(t, None).passed

    def test_棄却を要求しない課題では判定しない(self):
        assert AbstentionGate()(make(answer=3), None).silent
