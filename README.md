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

状态引擎目前是 Python API 和测试驱动的模块，**还没有单独的交互式命令行入口**。命令行 `python -m mahjong_ai ...` 仍只用于手牌分析。

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
