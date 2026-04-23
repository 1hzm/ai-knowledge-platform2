"""
课程讲义生成器
为教师生成 Markdown 格式的课程讲义
"""

import os
import re
from datetime import datetime
from pathlib import Path


class LectureGenerator:
    """课程讲义生成器"""
    
    def __init__(self, output_dir: str = "generated_lectures"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def parse_lecture_request(self, message: str) -> dict:
        """
        解析讲义生成请求
        
        支持的格式：
        - 生成讲义：机器学习第一章 历史
        - 讲义：Python 基础
        - 课程讲义：深度学习导论
        """
        patterns = [
            r'生成讲义[：:]\s*(.+)',
            r'讲义[：:]\s*(.+)',
            r'课程讲义[：:]\s*(.+)',
            r'生成教案[：:]\s*(.+)',
            r'教案[：:]\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return {
                    'topic': match.group(1).strip(),
                    'type': 'lecture'
                }
        
        return None
    
    def generate_lecture_prompt(self, topic: str) -> str:
        """生成用于 AI 的提示词"""
        return f'''请为"{topic}"这个主题生成一份详细的教师课程讲义。

请按以下 Markdown 格式返回：

```markdown
# {topic}

## 一、教学目标

### 知识目标
- 学生能够掌握...
- 学生能够理解...

### 能力目标
- 培养学生...的能力
- 提高学生...的技能

### 思政/情感目标
- 激发学生对...的兴趣
- 培养...的思维方式

## 二、教学重难点

**重点：**
- 
- 

**难点：**
- 
- 

## 三、课时安排
建议课时：X 课时（每课时 45 分钟）

## 四、教学内容

### 4.1 导入（10 分钟）
【设计意图】激发学生兴趣，引入本节课主题

【讲解要点】
- 
- 

### 4.2 新课讲授（25 分钟）

#### 4.2.1 知识点一：XXX
**概念讲解：**

详细解释...

**示例/案例：**

```
举例说明...
```

**注意事项：**
- 
- 

#### 4.2.2 知识点二：XXX
...

### 4.3 课堂练习/讨论（10 分钟）
【练习题】
1. 
2. 

【讨论话题】
- 

### 4.4 课堂小结（5 分钟）
【总结要点】
- 回顾本节课主要内容
- 强调重点和难点
- 布置下节课预习任务

## 五、板书设计

```
【主板书】
                    {topic}
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
  概念一              概念二               概念三
    │                    │                    │
  要点                要点                 要点

【副板书】
- 补充说明
- 学生提问解答
```

## 六、课后作业

### 基础作业（必做）
1. 
2. 

### 拓展作业（选做）
1. 
2. 

## 七、教学反思

**预设效果：**
- 

**可能问题：**
- 

**改进措施：**
- 

## 八、参考资料

1. 
2. 
3. 

## 九、附录

### 附录 A：专业术语表
| 术语 | 英文 | 解释 |
|------|------|------|
| | | |

### 附录 B：延伸阅读
- 
- 
```

要求：
1. 内容详实，适合教师直接用于授课
2. 包含具体的讲解话术和时间安排
3. 提供板书设计建议
4. 包含课堂互动环节
5. 只返回 Markdown 内容，不要其他说明'''

    def create_lecture_file(self, topic: str, content: str) -> str:
        """
        创建讲义文件
        
        Args:
            topic: 课程主题
            content: 讲义内容
            
        Returns:
            生成的文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = re.sub(r'[^\w\u4e00-\u9fff]+', '_', topic)[:50]
        filename = f"{safe_topic}_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        # 添加文件头信息
        header = f"""---
title: {topic}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
type: lecture_notes
---

"""
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + content)
        
        return filepath
    
    def list_lectures(self) -> list:
        """列出所有生成的讲义"""
        if not os.path.exists(self.output_dir):
            return []
        
        lectures = []
        for f in os.listdir(self.output_dir):
            if f.endswith('.md'):
                filepath = os.path.join(self.output_dir, f)
                stat = os.stat(filepath)
                lectures.append({
                    'filename': f,
                    'path': filepath,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # 按时间倒序
        lectures.sort(key=lambda x: x['created'], reverse=True)
        return lectures
    
    def get_lecture_preview(self, filepath: str, max_lines: int = 50) -> str:
        """
        获取讲义预览
        
        Args:
            filepath: 讲义文件路径
            max_lines: 最大预览行数
            
        Returns:
            预览文本
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                preview = ''.join(lines[:max_lines])
                if len(lines) > max_lines:
                    preview += f"\n\n...（共 {len(lines)} 行，此处省略）"
                return preview
        except Exception as e:
            return f"读取讲义失败: {e}"


if __name__ == "__main__":
    # 测试
    generator = LectureGenerator()
    print("讲义生成器测试")
    print(f"输出目录: {generator.output_dir}")
    
    # 测试解析
    test_messages = [
        "生成讲义：机器学习第一章",
        "讲义：Python 基础",
        "课程讲义：深度学习导论",
    ]
    
    for msg in test_messages:
        result = generator.parse_lecture_request(msg)
        print(f"\n输入: {msg}")
        print(f"解析: {result}")
