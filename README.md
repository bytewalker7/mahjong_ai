# mahjong_ai

纯 Python 的简化麻将手牌分析器。仅使用万、条、筒 27 种牌，按 `4 面子 + 1 将` 判断胡牌；不含网页、对局流程、计分或特殊牌型。

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

运行测试：

```powershell
python -m pytest
```
