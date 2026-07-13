# mahjong_ai

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

## 测试

运行全部测试：

```powershell
python -m pytest
```
