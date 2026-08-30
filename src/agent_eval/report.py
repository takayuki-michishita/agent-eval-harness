"""レポート。数字より先に「見ていない観点」を出す。"""

from __future__ import annotations

from .metrics import Summary


def render(summary: Summary) -> str:
    lines: list[str] = []
    a = lines.append

    a("# 評価レポート")
    a("")

    silent = summary.silent_graders
    if silent:
        a("## 見ていない観点")
        a("")
        a("次の採点器は、全課題を通じて一度も判定を下せていません。")
        a("**0件は「問題なし」ではありません。** その観点は測れていないだけです。")
        a("")
        for name in sorted(silent):
            a(f"- `{name}`")
        a("")

    partial = summary.partially_silent
    if partial:
        a("## 一部の課題で判定できなかった採点器")
        a("")
        a("該当の課題では、その観点は**合格でも不合格でもありません**。")
        a("")
        a("| 採点器 | 判定できなかった課題 |")
        a("|---|---|")
        for name in sorted(partial):
            a(f"| `{name}` | {', '.join(partial[name])} |")
        a("")

    unstable = summary.unstable
    if unstable:
        a("## 不安定な課題（合否が実行ごとに割れた）")
        a("")
        a("| 課題 | 合格率 | 実行回数 |")
        a("|---|---|---|")
        for r in unstable:
            a(f"| {r.task_id} | {r.pass_rate:.0%} | {r.runs} |")
        a("")

    a("## 全体")
    a("")
    a("| 指標 | 値 |")
    a("|---|---|")
    a(f"| 平均合格率 | {summary.pass_rate:.0%} |")
    a(f"| 不安定な課題 | {len(unstable)} / {len(summary.results)} |")
    a(f"| ツール失敗率 | {summary.tool_error_rate:.0%} |")
    a("")

    a("## 課題ごと")
    a("")
    a("| 課題 | 合格率 | 再現性 | 棄却率 | ツール失敗率 |")
    a("|---|---|---|---|---|")
    for r in summary.results:
        repro = "安定" if r.reproducible else "**割れた**"
        a(f"| {r.task_id} | {r.pass_rate:.0%} | {repro} | {r.abstain_rate:.0%} | {r.tool_error_rate:.0%} |")

    return "\n".join(lines)
