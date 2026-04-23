"""
课程大纲生成器
使用 MiniMax 大模型 API 流式生成课程大纲
"""

import requests
import json
import logging
from typing import Generator, Optional

logger = logging.getLogger('MiniMaxAgent.course')


class CourseGenerator:
    """课程大纲生成器"""

    BASE_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"

    # MiniMax API Key（复用 MiniMaxAgent 的）
    MINIMAX_API_KEY = None  # 由外部设置

    SYSTEM_PROMPT = "你是一位经验丰富的教育专家，擅长设计专业的课程大纲。"

    COURSE_OUTLINE_PROMPT = """请为"{topic}"设计一份简洁的课程大纲。

请严格按以下JSON格式输出，不要输出其他任何内容：
{{
  "title": "课程名称",
  "subject": "学科（如：数学、语文、英语、信息技术等）",
  "grade": "学段（如：小学三年级、初中一年级、高中二年级、大学一年级等）",
  "duration": 总课时数（数字，单位：分钟）,
  "teachingGoal": "教学目标（一句话概括学生通过本课程能掌握的核心能力）",
  "chapters": [
    {{
      "id": "1",
      "title": "章节名称",
      "duration": 本章总课时分钟数（数字）,
      "isKeyPoint": true/false,
      "sections": [
        {{
          "id": "1-1",
          "title": "小节名称",
          "content": "小节核心教学内容（一句话概括）",
          "summary": "本节学习目标摘要",
          "keyPoints": ["重点1", "重点2"],
          "isKeyPoint": true/false,
          "duration": 本节课时分钟数（数字）
        }}
      ]
    }}
  ]
}}

要求：
1. 章节数量3-5章，每章2-4节
2. 总课时合理分配（一般30-120分钟）
3. JSON格式严格正确，不要有Markdown代码块包裹
4. 只返回JSON，不要任何其他说明文字"""

    @classmethod
    def set_api_key(cls, api_key: str):
        cls.MINIMAX_API_KEY = api_key

    def parse_course_request(self, message: str) -> Optional[dict]:
        """
        解析课程大纲生成请求
        匹配格式：生成课程大纲 / 设计课程 / 制作课程 / 创建课程大纲 等
        """
        import re
        # 去掉常见前缀
        patterns = [
            r'(?:生成|设计|制作|创建|给我制定).{0,10}?课程.{0,10}?大纲',
            r'(?:生成|设计|制作|创建).{0,10}?课程',
            r'帮我.{0,10}?课程.{0,10}?设计',
            r'^课程大纲[:：]?\s*(.+)',
            r'^(.+?)课程大纲?$',
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                topic = match.group(1).strip() if match.groups() else message.strip()
                if topic and len(topic) > 1:
                    return {'topic': topic}
        # 兜底：纯主题词也识别（但排除纯问候语、闲聊和命令）
        casual_keywords = [
            # 问候语
            '你好', '您好', '嗨', 'hi', 'hello', 'hey', '在吗', '在不在', '干嘛', '干啥', '忙吗', '最近怎样', '怎么样', '还好吗', '睡了吗', '早上好', '下午好', '晚上好', '晚安', '再见', '拜拜', '谢谢', '对不起', '抱歉', '哈哈', '呵呵', '嗯嗯', '好的', '收到', '知道', '明白',
            # 记忆系统命令
            '/set-name', '/preference', '/memory', '/history', '/new', '/clear-session', '/clear-memory', '/save-memory', '/search-memory',
            '/set-name', '设置名字', '设置用户名',
        ]
        if len(message) < 50 and len(message) >= 2 and not any(k in message for k in ['帮我', '我想', '我要', '能不能', '会不会']) and not any(casual in message for casual in casual_keywords):
            return {'topic': message.strip()}
        return None

    def generate_course_stream(self, topic: str) -> Generator[str, None, None]:
        """
        流式生成课程大纲
        Yields: MiniMax streaming chunks
        """
        if not self.MINIMAX_API_KEY:
            logger.error("MINIMAX_API_KEY not set")
            yield "Error: API key not configured"
            return

        headers = {
            "Authorization": f"Bearer {self.MINIMAX_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt_text = self.COURSE_OUTLINE_PROMPT.format(topic=topic)

        payload = {
            "model": "MiniMax-M2.5-highspeed",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text}
            ],
            "stream": True,
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data = line_text[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk_data = json.loads(data)
                            if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                delta = chunk_data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Course generation error: {e}")
            yield f"Error: {str(e)}"
