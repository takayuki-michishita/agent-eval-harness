# agent-eval-harness

**非決定的なエージェント出力を、独立した第2系統で検証する評価ハーネス。**
An eval harness for non-deterministic agent output, built around independent second-system verification.

---

## なぜ作ったか

エージェントを本番に出せない理由の第1位は、性能でも費用でもなく **評価と可観測性** です。
出力が非決定的なうえ、ツール呼び出しと複数ステップの分岐が絡むため、
「同じ入力なら同じ出力」を前提にした従来のテストが成り立ちません。

そこで評価は「答え合わせ」から **行動監査** へ移りました。
最終回答だけを見ても、正しい答えに偶然たどり着いたのか、正しい手順を踏んだのかが区別できません。

このハーネスは、その差を測るために書かれています。

---

## 4つの設計

### 1. 行動監査 — 最終回答ではなく、通った手順を見る

どのツールを呼び、どこで失敗し、禁止された副作用に触れなかったか。
`ToolPolicy` が必須ツール・禁止ツール・ツール失敗率を採点します。

### 2. 第2系統の突き合わせ — 同じ仕組みを2回動かしても意味がない

同じ実装をもう一度動かしても、同じ間違いをするだけです。
**別の作りの実装**に同じ入力を通し、食い違った箇所だけを人に上げます。

この発想は音声合成の読み誤り検出から来ています。
単語を勘で選んで確かめる方式では必ず漏れが出ました。
形態素解析系と音声合成系の2系統で読みを出して突き合わせたところ、
**疑う理由がまったく無かった語から誤読が出ました。**
疑うかどうかと無関係に候補が挙がるのが要点です。

### 3. 棄却設計 — 「読めない」は失敗ではなく、正しい出力

答えられない入力に、黙って推測を返すエージェントは本番で危険です。
`AbstentionGate` は「棄却すべき入力で棄却したか」を採点します。
棄却率そのものも指標として出ます。

### 4. 沈黙の可視化 — 判定しなかった採点器を、合格に数えない

これが中核です。
採点器は `passed`（合格したか）に加えて **`covered`（そもそも判定を下せたか）** を返します。

**0件は「問題なし」の証拠になりません。** 見ていないだけかもしれないからです。
レポートは、数字より先に「見ていない観点」を出します。

---

## 使う

```bash
git clone https://github.com/tkyk-mcst/agent-eval-harness
cd agent-eval-harness
python examples/run_example.py     # 外部APIは要りません
```

```python
from agent_eval import Harness, Task, ExactMatch, SecondSystem, ToolPolicy, AbstentionGate, render

harness = Harness(
    graders=[
        ExactMatch(),
        SecondSystem(reference=my_independent_impl),
        ToolPolicy(required=("lookup",), forbidden=("delete",)),
        AbstentionGate(),
    ],
    repeat=5,          # 1回では測れない。3〜5回流して分布を見る
)
print(render(harness.run(my_agent, tasks)))
```

`my_agent` は `Task` を受け取って `Trace` を返す関数であれば何でも構いません。
エージェントSDKでも、自前のループでも、既存のAPIラッパーでも差し替えられます。

---

## 出力の例

```
## 一部の課題で判定できなかった採点器

該当の課題では、その観点は合格でも不合格でもありません。

| 採点器 | 判定できなかった課題 |
|---|---|
| abstention_gate | 読み取り-a, 読み取り-b |

## 不安定な課題（合否が実行ごとに割れた）

| 課題 | 合格率 | 実行回数 |
|---|---|---|
| 読み取り-a | 40% | 5 |

## 全体

| 指標 | 値 |
|---|---|
| 平均合格率 | 60% |
| 不安定な課題 | 2 / 3 |
| ツール失敗率 | 10% |
```

**合格率だけを見ると60%です。** しかし本番で困るのは、平均ではなく
「3件のうち2件が、流すたびに合否の変わる状態」のほうです。
1回だけ通ったものを「動いた」と呼ばないために、`repeat` の既定は5にしてあります。

---

## 設計の前提

- **機械の検査は下限であって、上限ではない。** このハーネスが0件を返しても、
  それは「機械が見た範囲で0件」という意味しか持ちません。
- **同種の検査を並べても、同じものしか見つからない。** 観点を変えて並べること。
- **数字より先に、測れなかったものを出す。** 沈黙は合格ではありません。

---

## English

Evaluation and observability is the single largest blocker to putting agents into production.
Outputs are non-deterministic and tool calls branch across steps, so tests that assume
"same input, same output" do not hold. Evaluation has moved from checking the final answer
to **auditing the behaviour**.

This harness measures that difference through four ideas:

1. **Behaviour audit.** Grade the trace — which tools ran, which failed, which forbidden
   side effects were avoided — not just the final answer.
2. **Independent second system.** Running the same implementation twice reproduces the same
   mistakes. Route the same input through a *differently built* implementation and surface
   only the disagreements. This came from detecting misreadings in speech synthesis, where
   cross-checking two independent readers surfaced errors in words nobody had reason to suspect.
3. **Abstention as a first-class outcome.** "I cannot read this" is a valid, often preferable
   output. `AbstentionGate` scores whether the agent abstained when it should have.
4. **Make silence visible.** Every grader returns `covered` alongside `passed`.
   **Zero findings is not evidence of no problem** — the report lists unexamined dimensions
   before it lists any numbers.

Requires Python 3.11+. No external services needed to run the example.

---

## Author

道下 孝之 / Takayuki Michishita — Tokyo, Japan

製造業を中心に、AIの実装から運用まで。異常検知・画像分類のモデル構築、
生成AIとAIエージェントの社内導入、技術者の育成。現役でコードを書いています。

- 大手素材メーカーの製造ライン異常検知：誤報を43件から10件へ、約77%削減
- 図面記号の物体検出：96分類、学習データ1,392枚を自ら整備
- 大手精密機器メーカーの需要予測：MAPE 18〜25%改善、廃棄ロス削減で年間コスト約4,800万円減
- 大手総合電機メーカーの生成AI基盤：10部門・約500名へ本番展開、文書検索精度 従来比＋28%

MIT License.
