# 会话记录 - 2026-04-21 23:21:59

## 23:21:59
## 对话记录 - 23:21:59

**用户**: ??Python???????????????,????????????????????,?????????JSON?????

**AI**: 
# Python 中文转拼音（附JSON保存）

您好！我来帮您实现中文转拼音的功能，并保存为JSON格式。

## 方法一：使用 `pypinyin` 库（推荐）

### 1. 安装库

```bash
pip install pypinyin
```

### 2. 基础代码示例

```python
from pypinyin import pinyin, Style
import json

# 示例中文文本
text = "你好世界，Python很有趣！"

# 获取带声调的拼音
result_with_tone = pinyin(text, style=Style.TONE)
print("带声调:", result_with_tone)
# [['nǐ'], ['hǎo'], ['shì'], ['jiè']]

# 获取不带声调的拼音
result_no_tone = pinyin(text, style=Style.NORMAL)
print("不带声调:", result_no_tone)
# [['ni'], ['hao'], ['shi'], ['jie']...



