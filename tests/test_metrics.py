from agent_eval import ExactMatch, Harness, Task, Trace, render


def stable_agent(task):
    t = Trace(task_id=task.id)
    t.add("lookup")
    t.answer = task.expected
    return t


def make_flaky(fail_on):
    calls = {"n": 0}

    def agent(task):
        t = Trace(task_id=task.id)
        t.add("lookup")
        calls["n"] += 1
        t.answer = None if calls["n"] in fail_on else task.expected
        return t

    return agent


TASKS = [Task(id="a", expected=1)]


class TestReproducibility:
    def test_毎回通れば安定(self):
        s = Harness(graders=[ExactMatch()], repeat=4).run(stable_agent, TASKS)
        assert s.results[0].reproducible
        assert s.results[0].pass_rate == 1.0
        assert s.unstable == []

    def test_割れたら不安定として上がる(self):
        s = Harness(graders=[ExactMatch()], repeat=4).run(make_flaky({2}), TASKS)
        r = s.results[0]
        assert not r.reproducible, "1回でも割れたら安定とは呼ばない"
        assert r.pass_rate == 0.75
        assert len(s.unstable) == 1

    def test_全部落ちても再現性はある(self):
        s = Harness(graders=[ExactMatch()], repeat=3).run(make_flaky({1, 2, 3}), TASKS)
        assert s.results[0].reproducible, "毎回落ちるのは不安定ではなく、確実な不合格"
        assert s.results[0].pass_rate == 0.0


class TestSilence:
    def test_一度も判定しない採点器は沈黙として上がる(self):
        tasks = [Task(id="a", expected=None)]
        s = Harness(graders=[ExactMatch()], repeat=2).run(stable_agent, tasks)
        assert s.silent_graders == {"exact_match"}

    def test_判定できた課題があれば全体の沈黙ではない(self):
        tasks = [Task(id="a", expected=1), Task(id="b", expected=None)]
        s = Harness(graders=[ExactMatch()], repeat=2).run(stable_agent, tasks)
        assert s.silent_graders == set()
        assert s.partially_silent == {"exact_match": ["b"]}


class TestReport:
    def test_沈黙を数字より先に出す(self):
        tasks = [Task(id="a", expected=None)]
        out = render(Harness(graders=[ExactMatch()], repeat=2).run(stable_agent, tasks))
        assert out.index("見ていない観点") < out.index("## 全体")
