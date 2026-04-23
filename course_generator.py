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

    def parse_course_request(self, message: str, conversation_history: list = None) -> Optional[dict]:
        """
        解析课程大纲生成请求
        只有明确包含"帮我生成课程"、"设计课程大纲"等显式关键词才触发
        其他全部返回 None（普通聊天）

        Args:
            message: 用户输入的消息
            conversation_history: 对话历史列表，用于理解上下文（如"这个"、"它"指代什么）
        """
        import re

        # 如果消息中包含代词（这个、它、这个课程...），需要从历史中找指代内容
        has_pronoun = any(k in message for k in ['这个', '它', '这个课程', '根据这个', '按照这个'])

        # 专门意图模式（必须明确匹配）
        explicit_patterns = [
            r'生成课程大纲',
            r'设计课程大纲',
            r'制作课程大纲',
            r'创建课程大纲',
            r'帮我生成课程',
            r'帮我设计课程',
            r'帮我制作课程',
            r'帮我创建课程',
            r'给我生成课程',
            r'给我设计课程',
            r'课程大纲[:：]?\s*(.+)',
            r'^(.+?)课程大纲$',
        ]

        for pattern in explicit_patterns:
            match = re.search(pattern, message)
            if match:
                topic = None
                if match.groups() and match.group(1):
                    topic = match.group(1).strip()

                # 如果有代词，不使用 explicit pattern 的 fallback topic（可能无意义）
                # 强制走历史提取
                if has_pronoun:
                    topic = None

                if topic and len(topic) >= 2:
                    return {'topic': topic}
                elif has_pronoun and conversation_history:
                    # 有代词但 explicit pattern 没提取到有意义 topic → 走历史
                    extracted = self._extract_topic_from_history(message, conversation_history)
                    if extracted:
                        return {'topic': extracted}
                    return None  # 有代词但历史也找不到 → 不触发
                elif topic:
                    return {'topic': topic}

        # 如果有代词但没有匹配显式模式，尝试从历史中找主题
        if has_pronoun and conversation_history:
            topic = self._extract_topic_from_history(message, conversation_history)
            if topic:
                return {'topic': topic}

        # 不匹配任何显式模式 → 普通聊天，不触发课程生成
        return None

    def _extract_topic_from_history(self, message: str, conversation_history: list) -> Optional[str]:
        """
        最简单暴力的提取：找所有看起来像课程名的中文词组
        """
        import re

        # 从最近5条消息中找
        recent = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history

        # 合并所有消息内容（优先AI回复）
        all_text = []
        for msg in reversed(recent):
            if msg.get('role') == 'assistant':
                all_text.append(msg.get('content', ''))

        # 找 ## 📚 标题行
        for text in all_text:
            # 匹配 ## 📚 xxx课程 这样的行
            match = re.search(r'#{1,3}\s*📚\s*([^\n\d]+?课程)', text)
            if match:
                topic = match.group(1).replace('**', '').strip()
                if topic and len(topic) >= 4:
                    logger.info(f"[CG] Found topic: {topic}")
                    return topic

        # 兜底：找"关于xxx课程"
        for text in all_text:
            match = re.search(r'关于([^课程]+)课程', text)
            if match:
                topic = match.group(1) + '课程'
                if len(topic) >= 4:
                    logger.info(f"[CG] Found topic via 关于: {topic}")
                    return topic

        # 兜底：找"xxx英语字母学习课程"等常见模式
        for text in all_text:
            match = re.search(r'([\u4e00-\u9fa5]+英语字母学习课程)', text)
            if match:
                logger.info(f"[CG] Found topic via 英语字母: {match.group(1)}")
                return match.group(1)

        logger.warning("[CG] No topic found in history!")
        return None

    def generate_course_stream(self, topic: str) -> Generator[str, None, None]:
        """
        流式生成课程大纲
        Yields: MiniMax streaming chunks
        """
        full_text = ''
        course_doc = None

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
                                    full_text += content
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Course generation error: {e}")
            yield f"Error: {str(e)}"

        # 流结束后，解析并yield完整课程结构
        try:
            # 尝试从full_text中提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', full_text)
            if json_match:
                course_doc = json.loads(json_match.group(0))
            else:
                course_doc = None
        except Exception as e:
            logger.error(f"Course JSON parse error: {e}")
            course_doc = None

        if course_doc:
            request_logger.info(f'[COURSE_GEN] Yielding course_generated event: {course_doc.get("title", "unknown")}')
            yield {
                'type': 'course_generated',
                'data': course_doc
            }
        else:
            request_logger.warning(f'[COURSE_GEN] course_doc is None, no course_generated event yielded. full_text length={len(full_text) if full_text else 0}')
