# mahjong_ai

## 单机四人对局

启动真人对战三个本地 AI 的独立桌面游戏：

```powershell
python -m mahjong_ai play
```

人类玩家固定为“自己”座位，三个 AI 使用各自独立的策略实例和随机 seed。界面只显示自己的完整手牌，以及三家 AI 的牌背数量、公开弃牌和副露；所有摸牌、弃牌、碰、杠、胡牌和结算均经由现有模拟器的合法动作接口。AI 行动速度可在窗口中调整。

## v0.7：强化学习弃牌训练

v0.7 的训练环境只让 RL 模型决定自己的弃牌；三家对手和自己的非弃牌动作均使用内部随机合法策略，不将贝叶斯风险模型作为训练特征或奖励。可先用现有规则弃牌策略生成行为克隆示范，让网络从规则模型开始，再进行 RL 微调；规则策略不会成为训练对手。模拟器按 `rules.markdown` 记录点炮、自摸、庄家胡牌翻倍、暗杠/放杠/补杠与 0–4 炮子分；RL 训练和评测默认将四家炮子固定为 0。训练完成后会用同一组固定种子，将 RL 模型与原有规则弃牌策略分别对阵随机对手，并把平均分、胜率、流局率、放炮率写入报告。

安装训练依赖后再由用户手动开始训练：

```powershell
python -m pip install -e ".[rl]"
python -m mahjong_ai train-rl --episodes 50000 --pretrain-games 5000 --seed 42 --output models/rl_discard_v1.json --report artifacts/rl_discard_v1_report.json --eval-games 1000
python -m mahjong_ai evaluate-rl --model models/rl_discard_v1.json --games 5000 --seed 2026
```

纯 Python 的简化麻将分析与牌局状态项目。仅使用万、条、筒 27 种牌，按 `4 面子 + 1 将` 判断胡牌；不含网页、完整对局 AI、计分或特殊牌型。

## 安装与运行

需要 Python 3.11+：

```powershell
python -m pip install -e ".[test]"
python -m mahjong_ai "1w 2w 3w 4w 5w 6w 2s 3s 4s 5p 5p 5p 8p 8p"
```

其中 `w`、`s`、`p` 分别表示万、条、筒。也接受中文后缀 `万`、`条`、`筒`。可选的已见牌（其它玩家的弃牌、碰牌、杠牌等）以 `--visible` 指定：

```powershell
python -m mahjong_ai "..." --visible "1w 1w 9p"
```

## v0.3 状态引擎

`mahjong_ai.state` 提供只记录公开信息的四人牌局状态引擎，支持：开局、设置自己的初始手牌、摸牌、弃牌、碰、明杠、暗杠、补杠、胡牌、轮转与撤销。

状态引擎提供持续运行的交互式命令行。启动它：

```powershell
python -m mahjong_ai game
```

输入 `help` 查看所有事件命令；使用 `status` 查看状态，轮到 `SELF` 时输入 `analyze` 获取向听、听牌、有效牌和弃牌推荐。输入 `undo` 撤销上一个事件，`quit` 退出。

一个最小流程（庄家为自己）：

```text
start self
hand 1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p 9p
analyze
discard self 5p
next self
hidden-draw right
discard right 9p
```

副露命令示例：`peng right self 3w`、`exposed-gang left right 5p`、`concealed-gang self 7s`、`added-gang self 7s`。所有命令都会通过状态引擎验证轮次、牌数和公开牌数量。

## v0.4 桌面录入界面

安装桌面界面可选依赖后启动：

```powershell
python -m pip install -e ".[ui,test]"
python -m mahjong_ai ui
```

界面使用 PySide6，提供四家独立的弃牌河与副露区、排序后的自己的手牌、分析面板，以及新一局、撤销、保存和加载按钮。当前行动玩家以蓝色边框和浅蓝背景标识；最后一张仍可响应的弃牌会显示 `【最后】`，不再使用影响文字可读性的黄色高亮。

界面会自动根据当前状态引导下一步，因而无需反复选择玩家和动作：自己出牌时直接点击手牌；其他玩家出牌时点击下方牌面；其他玩家摸牌时只需点击“记录暗摸”。弃牌后仅显示当前可用的碰、明杠、胡和“无人响应，下一家”按钮。所有界面操作都会转换为 `GameEvent` 后再由状态引擎验证和更新。

运行状态引擎测试：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests\test_state_engine.py -q
```

最小 API 用法：

```python
from mahjong_ai.state import (
    CallPeng,
    DiscardTile,
    PlayerPosition,
    SetOwnInitialHand,
    StartRound,
    apply_event,
    new_game,
)
from mahjong_ai.tiles import tile_to_code

self_ = PlayerPosition.SELF
right = PlayerPosition.RIGHT

state = apply_event(new_game(), StartRound(self_))
initial_tiles = (
    [tile_to_code("1w")]
    + [tile_to_code("2w")] * 4
    + [tile_to_code("3w")] * 4
    + [tile_to_code("4w")] * 4
    + [tile_to_code("5w")]
)
state = apply_event(state, SetOwnInitialHand(tuple(initial_tiles)))
state = apply_event(state, DiscardTile(self_, tile_to_code("1w")))
state = apply_event(state, CallPeng(right, tile_to_code("1w"), self_))

assert state.visible_counts[tile_to_code("1w")] == 3
```

上例中，自己的 `1w` 被 RIGHT 碰走后，弃牌河中的那张会标记为已使用；公开牌中 `1w` 总数为 3，不会被重复统计为“弃牌 1 张 + 碰牌 3 张”。

## v0.5 全知模拟与数据集

自动模拟器使用与项目一致的 108 张三门牌、平胡、碰和四种杠规则。它保存完整暗手、牌墙和逐步快照，但策略只能收到自己的手牌与公开观察。

生成全知 JSONL 牌谱：

```powershell
python -m mahjong_ai simulate --games 10000 --seed 42 --output data/full_games.jsonl
```

从牌谱提取公开特征与隐藏标签：

```powershell
python -m mahjong_ai build-dataset --input data/full_games.jsonl --output data/bayes_samples.jsonl
```

样本在“摸牌后弃牌前”和“弃牌后响应前”提取。每条输入只含观察者手牌与公开桌面信息；目标玩家的向听、听牌和危险牌掩码只作为隐藏标签。目标处于 14 张弃牌状态时，危险牌掩码全为假，不假设其未来会弃哪一张牌。

## 测试

运行全部测试：

```powershell
python -m pytest
```
# v0.6.0：公开信息对手风险模型

v0.6.0 从 v0.5.0 产生的全知牌谱训练可解释的朴素贝叶斯模型。模型只使用实战中可见的公开信息，输出每种合法弃牌对三家的**模型估计放炮概率**，以及任意一家放炮的综合概率；它不会宣称为真实或精确概率，也不会把风险混入牌效率推荐。

综合概率采用条件独立近似：`1 - product(1 - opponent_risk)`。三个对手的听牌状态和等待牌并非真正独立，因此该值只能作为模型估计。

训练与预测：

```powershell
python -m mahjong_ai train-opponent-model --input data/bayes_samples.jsonl --output models/opponent_risk_v1.json
python -m mahjong_ai predict-discard-risk --model models/opponent_risk_v1.json --state data/example_observation.json
```

`--state` 是一个 JSON 格式的 `Observation`：包含自己的 27 位计数手牌、公开弃牌/副露、公开牌计数、各家暗牌张数、当前玩家和阶段。预测只在“自己摸牌后、自己当前可弃牌”的状态输出候选牌。每种牌仅输出一次，并注明手中张数。输出中的三家综合风险明确为条件独立近似。
