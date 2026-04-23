"""
MiniMax Agent - 教师辅助 AI 助手
使用 MiniMax 大模型 API
支持 PPT 制作、课程讲义生成等功能
"""

import requests
import json
import os
import re
from datetime import datetime
from typing import Generator, Optional
from ppt_generator import PPTGenerator
from ppt_preview import generate_text_preview, PPTPreviewer
from lecture_generator import LectureGenerator
from content_generator import ContentGenerator
from memory_manager import MemoryManager
from course_generator import CourseGenerator


class MiniMaxAgent:
    """MiniMax 大模型 Agent"""
    
    BASE_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    
    def __init__(self, api_key: str, session_id: str = None):
        self.api_key = api_key
        self.session_id = session_id or "default"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.conversation_history = []
        self.ppt_generator = PPTGenerator()
        self.ppt_previewer = PPTPreviewer()
        self.lecture_generator = LectureGenerator()
        self.content_generator = ContentGenerator()
        self.course_generator = CourseGenerator()
        CourseGenerator.set_api_key(api_key)  # 同步 API key
        # 初始化记忆系统
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.memory = MemoryManager(base_dir, self.session_id)
        # 生成历史（用于 /save-memory 保存多次生成内容）
        self._generation_history = []

        # 从会话记录恢复对话历史
        self._restore_conversation_history()

    def _restore_conversation_history(self):
        """从会话记录文件恢复对话历史到内存"""
        session_file = os.path.join(self.memory.session_dir, f"{self.session_id}.md")
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析会话记录，还原为 conversation_history 格式
            # 直接按顺序提取所有 **用户** 和 **AI** 消息
            import re
            user_msgs = re.findall(r'\*\*用户\*\*[：:]\s*(.+?)(?=\n\*\*|\Z)', content, re.DOTALL)
            ai_msgs = re.findall(r'\*\*AI\*\*[：:]\s*(.+?)(?=\n\*\*|\Z)', content, re.DOTALL)

            # 按顺序添加到对话历史
            for user_content, ai_content in zip(user_msgs, ai_msgs):
                self.conversation_history.append({
                    "role": "user",
                    "content": user_content.strip()
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_content.strip()
                })

    def update_content_settings(self, settings: dict):
        """更新内容生成设置"""
        self.content_generator.update_settings(settings)
    
    def check_teacher_request(self, message: str, conversation_history: list = None):
        """
        检查是否是教师辅助相关请求
        支持：制作PPT、预览PPT、列出PPT、生成讲义、列出讲义、生成课程大纲

        Args:
            message: 用户输入的消息
            conversation_history: 对话历史列表，用于理解上下文（如"这个"、"它"指代什么）
        """
        if conversation_history is None:
            conversation_history = []

        # 检查是否是课程大纲生成请求（优先级高）
        # 如果消息中包含代词（这个、它、根据这个...），需要结合上下文解析
        course_request = self.course_generator.parse_course_request(message, conversation_history)
        if course_request:
            topic = course_request['topic']
            return self.course_generator.generate_course_stream(topic)

        # 检查是否是内容生成请求
        content_request = self.content_generator.parse_content_request(message)
        if content_request:
            topic = content_request['topic']
            content_type = content_request['type']
            return self._create_content_with_ai(topic, content_type)

        # 检查是否是列出内容请求
        if re.search(r'(列出|查看|显示).*?(?:内容|文案|音频|封面)', message) or message.lower() in ['list content', 'content list', '我的内容']:
            return self._list_contents()

        # 检查是否是讲义相关请求
        lecture_request = self.lecture_generator.parse_lecture_request(message)
        if lecture_request:
            topic = lecture_request['topic']
            return self._create_lecture_with_ai(topic)

        # 检查是否是列出讲义请求
        if re.search(r'(列出|查看|显示).*?讲义', message) or message.lower() in ['list lecture', 'lecture list', '我的讲义']:
            return self._list_lectures()
        
        # 检查是否是预览请求
        preview_match = re.search(r'预览[Pp][Pp][Tt][:：]?\s*(.+)?', message)
        if preview_match or '预览' in message and 'ppt' in message.lower():
            return self._handle_preview_request(message)
        
        # 检查是否是列出PPT请求
        if re.search(r'(列出|查看|显示).*?[Pp][Pp][Tt]', message) or message.lower() in ['list ppt', 'ppt list', '我的ppt']:
            return self._list_ppts()
        
        # 检查是否是制作PPT请求
        ppt_request = self.ppt_generator.parse_ppt_request(message)
        if ppt_request:
            topic = ppt_request['topic']
            return self._create_ppt_with_ai(topic)
        
        # 检查是否是记忆系统命令
        memory_result = self._handle_memory_command(message)
        if memory_result:
            return memory_result
        
        return None
    
    def _list_ppts(self) -> str:
        """列出所有生成的 PPT"""
        import os
        ppt_dir = "generated_ppt"
        if not os.path.exists(ppt_dir):
            return "还没有生成任何 PPT 文件。"
        
        # 过滤掉临时文件（以 ~$ 开头）
        ppt_files = [f for f in os.listdir(ppt_dir) if f.endswith('.pptx') and not f.startswith('~$')]
        if not ppt_files:
            return "还没有生成任何 PPT 文件。"
        
        result = ["已生成的 PPT 文件：", "=" * 50]
        for i, f in enumerate(ppt_files, 1):
            file_path = os.path.join(ppt_dir, f)
            size = os.path.getsize(file_path) / 1024  # KB
            result.append(f"{i}. {f} ({size:.1f} KB)")
        
        result.append("<br>使用 '预览PPT: 文件名' 查看内容")
        return '<br>'.join(result)
    
    def _handle_memory_command(self, message: str):
        """处理记忆系统相关命令"""
        msg_lower = message.lower().strip()
        
        # /memory - 查看记忆摘要
        if msg_lower in ['/memory', '/记忆', '查看记忆', '我的记忆']:
            return self.memory.get_memory_summary()

        # /history - 查看生成历史
        if msg_lower in ['/history', '/历史', '生成历史', '我的生成']:
            if not self._generation_history:
                return "📋 当前没有生成历史"
            lines = ["📋 最近生成内容：", "=" * 40]
            for i, item in enumerate(self._generation_history, 1):
                lines.append(f"{i}. 【{item['type']}】{item['topic']}")
            return "<br>".join(lines)

        # /new - 新对话（清除所有历史记录，包括会话记录）
        if msg_lower in ['/new', '/new session', '新会话']:
            self.clear_history()
            # 清除会话记录，确保新对话不干扰
            self.memory.clear_session_file()
            return "✅ 新对话"

        # /clear-session - 清除当前会话记录（文件和内存）
        if msg_lower in ['/clear-session', '/clear-daily', '/clearsession']:
            self.clear_history()
            self.memory.clear_session_file()
            return "✅ 当前会话记录已清除"
        
        # /clear-memory - 清除长期记忆
        if msg_lower in ['/clear-memory', '/clearmemory', '清除记忆']:
            self.memory.clear_long_term_memory()
            return "✅ 长期记忆已清除"
        
        # /save-memory - 保存当前对话到长期记忆
        save_match = re.match(r'^/save-memory\s*(.*)', msg_lower)
        if save_match or msg_lower.startswith('/save-memory'):
            # 提取要保存的内容
            extra = save_match.group(1).strip() if save_match else ""
            if extra:
                self.memory.upgrade_to_long_term(extra)
                return f"✅ 已保存到长期记忆：{extra[:100]}"
            else:
                # 让 AI 分析对话精华，自动生成值得记忆的内容
                return self._save_conversation_essence()
        
        # /search-memory 关键词 - 搜索记忆
        search_match = re.match(r'^/search-memory\s+(.+)', msg_lower)
        if search_match or msg_lower.startswith('/search-memory'):
            keyword = search_match.group(1).strip() if search_match else message.replace('/search-memory', '').replace('搜索记忆', '').strip()
            if keyword:
                results = self.memory.search_memory(keyword)
                if results:
                    response = [f"🔍 搜索 '{keyword}' 的结果：", "=" * 40]
                    for r in results[:5]:
                        response.append(f"<br>📂 来源：{r['source']}")
                        response.append(f"📄 {r['content'][:300]}")
                    return "<br>".join(response)
                return f"没有找到包含 '{keyword}' 的记忆"
            return "请提供搜索关键词，例如：/search-memory Python"
        
        # /set-name 名字 - 设置用户名
        name_match = re.match(r'^/set-name\s+(.+)', msg_lower)
        if name_match or msg_lower.startswith('/set-name'):
            name = name_match.group(1).strip() if name_match else message.replace('/set-name', '').replace('设置名字', '').strip()
            if name:
                self.memory.set_user_name(name)
                return f"✅ 用户名已设置为：{name}"
            return "请提供用户名，例如：/set-name 张老师"
        
        # /preference 键=值 - 设置偏好
        pref_match = re.match(r'^/preference\s+(.+)=(.+)', msg_lower)
        if pref_match or msg_lower.startswith('/preference'):
            try:
                if pref_match:
                    key, value = pref_match.group(1).strip(), pref_match.group(2).strip()
                else:
                    # 尝试中文字符
                    match_cn = re.match(r'^/preference\s+(\S+)\s*=\s*(.+)', message)
                    if match_cn:
                        key, value = match_cn.group(1).strip(), match_cn.group(2).strip()
                    else:
                        return "格式错误，请使用：/preference 键=值，例如：/preference 学科=语文"
                self.memory.set_preference(key, value)
                return f"✅ 偏好已设置：{key} = {value}"
            except:
                return "格式错误，请使用：/preference 键=值"
        
        return None

    def _summarize_with_ai(self, content: str, gen_type: str) -> str:
        """使用 AI 精简内容"""
        prompts = {
            '对话': '''请分析以下对话，提取出值得永久记住的知识、偏好或重要信息。

【对话记录】
{content}

请按以下固定格式返回（只返回记忆内容，不要其他说明）：
**主题**：一句话概括主题
**关键知识点**：1-3条要点，用分号分隔''',

            'ppt': '''请分析以下PPT大纲，提取核心要点。

【PPT内容】
{content}

请严格按以下格式返回（必须包含**主题**和**核心要点**，不要其他文字）：
**主题**：[一句话概括PPT主题]
**核心要点**：[3-5个核心要点，用分号分隔]''',

            'lecture': '''请分析以下讲义内容，提取核心要点。

【讲义内容】
{content}

请按以下固定格式返回（只返回记忆内容，不要其他说明）：
**主题**：讲义主题
**核心要点**：3-5个核心要点，用分号分隔''',

            'graphic_content': '''请分析以下图文内容，提取核心要点。

【图文内容】
{content}

请按以下固定格式返回（只返回记忆内容，不要其他说明）：
**主题**：内容主题
**核心要点**：3-5个核心要点，用分号分隔''',

            'video_script': '''请分析以下视频脚本，提取核心要点。

【视频脚本】
{content}

请按以下固定格式返回（只返回记忆内容，不要其他说明）：
**主题**：视频主题
**核心要点**：3-5个核心要点，用分号分隔'''
        }

        # 根据类型限制内容大小，避免超时
        if gen_type == 'graphic_content':
            content = content[:1500]
        elif gen_type == 'video_script':
            content = content[:2000]
        else:
            content = content[:3000]

        prompt = prompts.get(gen_type, prompts['对话']).format(content=content)
        print(f"[AI精简] 发送请求 - 类型:{gen_type}, 内容长度:{len(content)}, prompt长度:{len(prompt)}")

        import re
        max_retries = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.BASE_URL,
                    headers=self.headers,
                    json={
                        "model": "MiniMax-M2.5-highspeed",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "temperature": 0.7,
                        "max_tokens": 1500
                    },
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                ai_output = result["choices"][0]["message"]["content"]
                print(f"[AI精简] 原始返回({len(ai_output)}字符): {ai_output[:300]}")
                print(f"[AI精简调试] 状态码: {response.status_code}, choices数: {len(result.get('choices', []))}")
                if not ai_output:
                    print(f"[AI精简调试] 完整响应: {json.dumps(result, ensure_ascii=False)[:500]}")
                    # 检查是否有 finish_reason
                    try:
                        finish_reason = result["choices"][0].get("finish_reason", "无")
                        print(f"[AI精简调试] finish_reason: {finish_reason}")
                    except:
                        pass

                summary = ai_output.strip()

                # 清理 markdown 格式
                summary = re.sub(r'^```(?:markdown)?\s*', '', summary)
                summary = re.sub(r'\s*```$', '', summary)

                # 如果返回内容但没有包含格式关键词，尝试用正则提取
                if summary and '**主题**' not in summary and '**核心要点**' not in summary:
                    topic_match = re.search(r'(?:主题|Title)[:：]\s*(.+?)(?:\n|$)', summary)
                    key_match = re.search(r'(?:核心要点|要点|关键)[:：]\s*(.+?)(?:\n|$)', summary, re.IGNORECASE)
                    if topic_match or key_match:
                        topic = topic_match.group(1).strip() if topic_match else '[提取的主题]'
                        keys = key_match.group(1).strip() if key_match else '[提取的要点]'
                        summary = f"**主题**：{topic}\n**核心要点**：{keys}"
                        print(f"[记忆] AI格式不标准，已用正则提取: {topic[:20]}")

                return summary if summary else None
            except requests.exceptions.Timeout:
                print(f"[AI精简超时] 尝试 {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # 等待 2 秒后重试
            except requests.exceptions.HTTPError as e:
                print(f"[AI精简HTTP错误] 尝试 {attempt+1}/{max_retries}: 状态码 {e.response.status_code}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)
            except Exception as e:
                print(f"[AI精简失败] 尝试 {attempt+1}/{max_retries}: {type(e).__name__}: {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)

        return None

    def _save_conversation_simple(self) -> str:
        """保存对话内容到长期记忆（AI 精简）"""
        if not self.conversation_history:
            return "当前没有对话内容"

        # 取最近 6 条对话
        recent = self.conversation_history[-6:]
        history_lines = []
        for msg in recent:
            role = "用户" if msg.get('role') == 'user' else "AI"
            content = msg.get('content', '')[:500]
            history_lines.append(f"{role}：{content}")

        raw_content = "\n".join(history_lines)

        # AI 精简
        summary = self._summarize_with_ai(raw_content, '对话')
        if summary:
            content = f"【对话】\n{summary}"
        else:
            # AI 精简失败时降级为简单截断
            content = f"【对话】\n**主题**：对话记录\n**关键知识点**：{raw_content[:200]}..."

        self.memory.upgrade_to_long_term(content)
        return f"✅ 已保存 {len(recent)} 条对话到长期记忆（AI 精简）"

    def _save_generation_simple(self) -> str:
        """保存生成内容到长期记忆（AI 精简）"""
        if not self._generation_history:
            return "当前没有生成内容"

        saved = []
        for item in self._generation_history:
            gen_type = item.get('type', 'unknown')
            topic = item.get('topic', '未知主题')
            data = item.get('data', {})

            # 收集原始内容用于 AI 精简
            raw_content = f"主题：{topic}\n"

            # 如果是 PPT，格式化大纲
            if gen_type == 'ppt' and 'slides' in data:
                slides = data['slides']
                raw_content += "PPT大纲：\n"
                for i, slide in enumerate(slides):
                    slide_type = slide.get('type', 'content')
                    slide_title = slide.get('title', f'第{i+1}页')
                    if slide_type == 'title':
                        raw_content += f"  封面：{slide_title}\n"
                    elif slide_type == 'section':
                        raw_content += f"  章节：{slide_title}\n"
                    else:
                        raw_content += f"  内容页：{slide_title}\n"
                        slide_content = slide.get('content', [])
                        if slide_content:
                            for sc_item in slide_content:
                                if isinstance(sc_item, dict):
                                    raw_content += f"    - {sc_item.get('text', '')}\n"
                                else:
                                    raw_content += f"    - {sc_item}\n"
                        else:
                            raw_content += f"    - [页面内容略]\n"

            # 如果是讲义
            elif gen_type == 'lecture' and 'lecture_content' in data:
                raw_content += f"讲义内容：\n{data['lecture_content']}"

            # 如果是图文内容
            elif gen_type == 'graphic_content' and 'xiaohongshu' in data:
                raw_content += f"图文文案：\n{data['xiaohongshu']}"

            # 如果是视频脚本
            elif gen_type == 'video_script' and 'video_script' in data:
                raw_content += f"视频脚本：\n{data['video_script']}"

            # AI 精简
            summary = self._summarize_with_ai(raw_content, gen_type)
            if summary and '**主题**' in summary and '**核心要点**' in summary:
                content = f"【{gen_type}】\n{summary}"
                print(f"[记忆] AI精简成功 - {gen_type}: {topic[:30]}")
            else:
                # AI 精简失败时降级为简单截断（保存前200字原始内容）
                preview = raw_content[:200].replace('\n', ' ').strip()
                if not preview:
                    preview = topic  # 如果raw_content为空，用标题
                content = f"【{gen_type}】\n**主题**：{topic}\n**核心要点**：{preview}..."
                print(f"[记忆] AI精简失败，使用Fallback - {gen_type}: {topic[:30]}")

            self.memory.upgrade_to_long_term(content)
            saved.append(f"【{gen_type}】{topic}")

        self._generation_history.clear()
        return f"✅ 已保存 {len(saved)} 个生成内容到长期记忆（AI 精简）"

    def _save_conversation_essence(self) -> str:
        """
        保存生成历史或对话到长期记忆（统一使用 AI 精简）
        """
        # 如果有生成历史，调用 _save_generation_simple
        if self._generation_history:
            return self._save_generation_simple()

        if not self.conversation_history:
            return "当前没有对话内容，也无法提取生成内容"

        # 对话历史使用 AI 精简
        return self._save_conversation_simple()

    def _handle_preview_request(self, message: str) -> str:
        """处理预览请求"""
        import os
        import re
        
        # 尝试提取文件名
        match = re.search(r'预览[Pp][Pp][Tt][:：]?\s*(.+)', message)
        
        ppt_dir = "generated_ppt"
        if not os.path.exists(ppt_dir):
            return "还没有生成任何 PPT 文件。"
        
        # 过滤掉临时文件（以 ~$ 开头）
        ppt_files = [f for f in os.listdir(ppt_dir) if f.endswith('.pptx') and not f.startswith('~$')]
        if not ppt_files:
            return "还没有生成任何 PPT 文件。"
        
        # 如果指定了文件名
        if match:
            file_hint = match.group(1).strip()
            # 查找匹配的 PPT
            for f in ppt_files:
                if file_hint.lower() in f.lower():
                    ppt_path = os.path.join(ppt_dir, f)
                    return self._generate_preview(ppt_path)
            return f"未找到包含 '{file_hint}' 的 PPT 文件。<br>可用文件：" + ', '.join(ppt_files)
        
        # 如果没有指定，预览最新的 PPT
        latest_ppt = max(ppt_files, key=lambda f: os.path.getmtime(os.path.join(ppt_dir, f)))
        ppt_path = os.path.join(ppt_dir, latest_ppt)
        return self._generate_preview(ppt_path)
    
    def _generate_preview(self, ppt_path: str) -> str | dict:
        """生成 PPT 预览"""
        try:
            # 尝试生成图片预览
            preview_data = self.ppt_previewer.get_preview_data(ppt_path)
            
            if 'error' in preview_data:
                # 如果图片预览失败，返回文本预览
                preview_text = generate_text_preview(ppt_path)
                return f"📊 PPT 预览<br><br>{preview_text}<br><br>💡 提示：文件位于 {ppt_path}"
            
            # 返回预览数据（包含图片）
            return {
                'type': 'ppt_preview',
                'filename': preview_data['filename'],
                'total_pages': preview_data['total_pages'],
                'slides': preview_data['slides']
            }
        except Exception as e:
            return f"预览生成失败: {str(e)}"
    
    def _list_lectures(self) -> str:
        """列出所有生成的讲义"""
        lectures = self.lecture_generator.list_lectures()
        if not lectures:
            return "还没有生成任何课程讲义。<br><br>使用 '生成讲义：主题' 来创建讲义。"
        
        result = ["📚 已生成的课程讲义：", "=" * 50]
        for i, lec in enumerate(lectures, 1):
            size_kb = lec['size'] / 1024
            result.append(f"{i}. {lec['filename']}")
            result.append(f"   创建时间: {lec['created']} | 大小: {size_kb:.1f} KB")
        
        result.append("<br>💡 提示：讲义保存在 generated_lectures/ 目录")
        return '<br>'.join(result)

    def _list_contents(self) -> str:
        """列出所有生成的内容"""
        contents = self.content_generator.list_generated_content()
        if not contents:
            return "还没有生成任何内容。<br><br>使用 '生成内容：主题' 或 '短视频：主题' 来创建内容。"

        result = ["📦 已生成的内容文件：", "=" * 50]

        # 分类统计
        text_count = sum(1 for c in contents if c['type'] == 'text')
        audio_count = sum(1 for c in contents if c['type'] == 'audio')
        image_count = sum(1 for c in contents if c['type'] == 'image')

        result.append(f"<br>📄 文案: {text_count} 个 | 🔊 音频: {audio_count} 个 | 🖼️ 图片: {image_count} 个<br>")

        for i, item in enumerate(contents[:10], 1):  # 最多显示10个
            size_kb = item['size'] / 1024
            type_emoji = {'text': '📄', 'audio': '🔊', 'image': '🖼️'}.get(item['type'], '📦')
            result.append(f"{i}. {type_emoji} {item['filename']}")
            result.append(f"   类型: {item['type']} | 时间: {item['created']} | 大小: {size_kb:.1f} KB")

        if len(contents) > 10:
            result.append(f"<br>... 还有 {len(contents) - 10} 个文件")

        result.append("<br>💡 提示：内容保存在 generated_content/ 目录")
        return '<br>'.join(result)

    def _create_content_with_ai(self, topic: str, content_type: str = 'graphic_content'):
        """
        使用 AI 生成自媒体内容
        content_type: 'graphic_content' = 图文内容（小红书文案+封面图）
                     'video_script' = 短视频脚本（脚本+AI配音）
        返回生成器，流式输出进度和结果
        """
        if content_type == 'video_script':
            # 短视频脚本：脚本 + AI配音
            outline_msg = f"📋 即将为您生成短视频脚本：<br><br>"
            outline_msg += f"主题：{topic}<br>"
            outline_msg += f"<br>将生成：<br>"
            outline_msg += "  1. 📝 短视频脚本（抖音/B站/视频号）<br>"
            outline_msg += "  2. 🔊 AI 配音音频<br><br>"
            outline_msg += "⏳ 正在生成中，请稍候...<br>"
            outline_msg += "=" * 50
            yield outline_msg

            # 从设置中获取 style
            mimo_style = self.content_generator.settings.get('mimo_style', '')

            for update in self.content_generator.generate_video_script_stream(topic, mimo_style):
                # 优先检查特殊步骤（大数据传输），因为这些的 status 也是 'running'
                if update.get('step') == 'audio_data' and update.get('data', {}).get('type') == 'video_audio_data':
                    # 音频数据单独发送
                    print(f"[DEBUG] 检测到音频数据步骤，base64长度: {len(update['data'].get('audio_base64', ''))}")
                    yield {
                        'type': 'video_audio_data',
                        'audio_base64': update['data']['audio_base64'],
                        'voiceover_text': update['data']['voiceover_text']
                    }
                elif update.get('status') == 'completed':
                    # 过滤掉大的 base64 数据，避免 JSON 过大
                    filtered_data = {k: v for k, v in update['data'].items() if 'base64' not in k}
                    result_data = {
                        'type': 'video_complete',
                        'data': filtered_data,
                        'message': update['message']
                    }
                    # 记录到记忆
                    self.memory.log_generation(topic, 'video_script', filtered_data)
                    # 保存到生成历史供 /save-memory 使用
                    self._generation_history.append({
                        'type': 'video_script',
                        'topic': topic,
                        'data': filtered_data
                    })
                    # 最多保留10条
                    if len(self._generation_history) > 10:
                        self._generation_history.pop(0)
                    yield result_data
                elif update.get('status') == 'error':
                    yield f"<br>❌ 生成失败: {update['message']}"
                else:
                    yield f"<br>[{update.get('progress', 0)}%] {update['message']}"
        else:
            # 图文内容：小红书文案 + 封面图
            outline_msg = f"📋 即将为您生成图文内容：<br><br>"
            outline_msg += f"主题：{topic}<br>"
            outline_msg += f"<br>将生成：<br>"
            outline_msg += "  1. 📕 小红书爆款文案<br>"
            outline_msg += "  2. 🎨 AI 封面图<br><br>"
            outline_msg += "⏳ 正在生成中，请稍候...<br>"
            outline_msg += "=" * 50
            yield outline_msg

            for update in self.content_generator.generate_graphic_content_stream(topic):
                # 优先检查特殊步骤（大数据传输），因为这些的 status 也是 'running'
                if update.get('step') == 'image_data' and update.get('data', {}).get('type') == 'graphic_image_data':
                    # 图片数据单独发送
                    print(f"[DEBUG] 检测到图片数据步骤，base64长度: {len(update['data'].get('image_base64', ''))}")
                    yield {
                        'type': 'graphic_image_data',
                        'image_base64': update['data']['image_base64'],
                        'prompt': update['data']['prompt']
                    }
                elif update.get('status') == 'completed':
                    # 过滤掉大的 base64 数据，避免 JSON 过大
                    filtered_data = {k: v for k, v in update['data'].items() if 'base64' not in k}
                    result_data = {
                        'type': 'graphic_complete',
                        'data': filtered_data,
                        'message': update['message']
                    }
                    # 记录到记忆
                    self.memory.log_generation(topic, 'graphic_content', filtered_data)
                    # 保存到生成历史供 /save-memory 使用
                    self._generation_history.append({
                        'type': 'graphic_content',
                        'topic': topic,
                        'data': filtered_data
                    })
                    # 最多保留10条
                    if len(self._generation_history) > 10:
                        self._generation_history.pop(0)
                    yield result_data
                elif update.get('status') == 'error':
                    yield f"<br>❌ 生成失败: {update['message']}"
                else:
                    yield f"<br>[{update.get('progress', 0)}%] {update['message']}"

    def _create_lecture_with_ai(self, topic: str) -> str:
        """
        使用 AI 生成课程讲义
        """
        # 构建提示词
        prompt = self.lecture_generator.generate_lecture_prompt(topic)
        
        try:
            # 调用 AI 生成讲义
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json={
                    "model": "MiniMax-M2.5-highspeed",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            # 提取 Markdown 内容
            import re
            # 尝试提取代码块中的内容
            code_block_match = re.search(r'```markdown\s*\n(.*?)\n```', ai_response, re.DOTALL)
            if code_block_match:
                lecture_content = code_block_match.group(1)
            else:
                # 如果没有 markdown 标记，使用整个响应
                lecture_content = ai_response
            
            # 保存讲义文件
            output_path = self.lecture_generator.create_lecture_file(topic, lecture_content)

            # 记录到记忆
            self.memory.log_generation(topic, 'lecture', {
                'output_path': output_path,
                'lecture_content': lecture_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            # 保存到生成历史供 /save-memory 使用
            self._generation_history.append({
                'type': 'lecture',
                'topic': topic,
                'data': {'output_path': output_path, 'lecture_content': lecture_content}
            })
            # 最多保留10条
            if len(self._generation_history) > 10:
                self._generation_history.pop(0)

            # 生成预览
            preview = self.lecture_generator.get_lecture_preview(output_path, max_lines=30)

            return f"✅ 课程讲义已生成！<br>📄 文件路径: {output_path}<br><br>📋 内容预览：<br>{'='*50}<br>{preview}<br>{'='*50}<br><br>💡 提示：这是 Markdown 格式文件，可以用任何文本编辑器打开"
            
        except Exception as e:
            return f"❌ 讲义生成失败: {str(e)}"
    
    def _create_ppt_with_ai(self, topic: str):
        """
        使用 AI 生成 PPT 内容并创建 PPT 文件
        返回：生成器，先输出大纲文本，再输出预览数据
        """
        # 构建提示词，让 AI 生成 PPT 大纲
        prompt = f'''请为"{topic}"这个主题生成一个PPT大纲。

请按以下格式返回（JSON格式）：
{{
    "title": "PPT标题",
    "slides": [
        {{"type": "title", "title": "封面标题"}},
        {{"type": "content", "title": "页面标题", "content": ["要点1", "要点2", "要点3"]}},
        {{"type": "section", "title": "章节标题"}}
    ]
}}

要求：
1. 包含封面页、3-5个内容页、结束页
2. 内容简洁明了，适合演讲
3. 只返回JSON，不要其他说明文字'''

        try:
            # 调用 AI 生成大纲
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json={
                    "model": "MiniMax-M2.5-highspeed",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]

            # 解析 JSON
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                ppt_data = json.loads(json_match.group())
                slides = ppt_data.get('slides', [])
                title = ppt_data.get('title', topic)

                # 1. 先输出大纲
                outline_lines = [f"📋 PPT 大纲：{title}", "=" * 50]
                for i, slide in enumerate(slides, 1):
                    slide_type = slide.get('type', 'content')
                    slide_title = slide.get('title', f'第{i}页')
                    if slide_type == 'title':
                        outline_lines.append(f"<br>🎬 封面：{slide_title}")
                    elif slide_type == 'section':
                        outline_lines.append(f"<br>📑 章节：{slide_title}")
                    else:
                        outline_lines.append(f"<br>📄 第{i}页：{slide_title}")
                        content = slide.get('content', [])
                        if content:
                            for item in content:
                                if isinstance(item, dict):
                                    outline_lines.append(f"   • {item.get('text', '')}")
                                else:
                                    outline_lines.append(f"   • {item}")

                yield '<br>'.join(outline_lines)

                # 2. 生成 PPT
                output_path = self.ppt_generator.create_ppt(title, slides, theme="teal")

                # 记录到记忆（包含完整 slides 用于大纲保存）
                self.memory.log_generation(topic, 'ppt', {
                    'output_path': output_path,
                    'title': title,
                    'slides': slides,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # 保存到生成历史供 /save-memory 使用
                self._generation_history.append({
                    'type': 'ppt',
                    'topic': topic,
                    'data': {'slides': slides, 'title': title, 'output_path': output_path}
                })
                # 最多保留10条
                if len(self._generation_history) > 10:
                    self._generation_history.pop(0)

                # 3. 输出文件路径和预览提示
                completion_msg = f"<br>{'=' * 50}<br>✅ PPT 已生成！<br>📄 文件路径: {output_path}<br>📊 共 {len(slides)} 页幻灯片<br><br>💡 提示：点击左侧「预览最新 PPT」按钮查看预览图"
                yield completion_msg
            else:
                yield "❌ 无法解析 AI 生成的 PPT 大纲"

        except Exception as e:
            yield f"❌ PPT 生成失败: {str(e)}"
    
    def chat(self, message: str, stream: bool = False, conversation_history: list = None):
        """
        发送消息给 MiniMax 模型

        Args:
            message: 用户输入的消息
            stream: 是否使用流式输出
            conversation_history: 对话历史列表，用于理解上下文（如"这个"、"它"指代什么）

        Returns:
            完整回复字符串、流式生成器、或 PPT 预览字典
        """
        # 使用传入的历史记录，如果没有则使用自身的对话历史
        if conversation_history is None:
            conversation_history = self.conversation_history

        # 首先检查是否是教师辅助相关请求（PPT、讲义等）
        # 传入对话历史以便在意图检测时理解上下文
        teacher_result = self.check_teacher_request(message, conversation_history)
        if teacher_result:
            # 如果是字典（PPT预览数据），直接返回
            if isinstance(teacher_result, dict):
                return teacher_result
            # 如果是生成器（如制作PPT时先输出大纲再输出预览），直接返回
            if hasattr(teacher_result, '__iter__') and not isinstance(teacher_result, (str, bytes)):
                if stream:
                    return teacher_result
                else:
                    # stream=False 时，消耗生成器并返回拼接后的字符串
                    return ''.join(teacher_result)
            # 否则是普通字符串响应
            if stream:
                # 将字符串转换为生成器
                def string_generator():
                    yield teacher_result
                return string_generator()
            return teacher_result
        
        # 获取记忆上下文并注入到对话
        memory_context = self.memory.get_context_for_prompt()
        
        # 添加用户消息到历史记录
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # 构建完整的消息列表（包含记忆上下文）
        if memory_context:
            system_message = {
                "role": "system",
                "content": f"你是一个友好、有知识的AI教师助手。你拥有自己的长期记忆库，当用户询问相关问题时，你应该主动引用记忆中的内容来回答案。{memory_context}"
            }
            messages_with_context = [system_message] + self.conversation_history
        else:
            messages_with_context = self.conversation_history
        
        payload = {
            "model": "MiniMax-M2.5-highspeed",
            "messages": messages_with_context,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json=payload,
                stream=stream,
                timeout=60
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_with_memory(response, message)
            else:
                result = response.json()
                assistant_message = result["choices"][0]["message"]["content"]
                
                # 添加助手回复到历史记录
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                
                # 记录到会话记忆
                self.memory.log_interaction(message, assistant_message)

                return assistant_message
                
        except requests.exceptions.RequestException as e:
            error_msg = f"请求失败: {str(e)}"
            return error_msg
        except (KeyError, json.JSONDecodeError) as e:
            error_msg = f"解析响应失败: {str(e)}"
            return error_msg
    
    def _handle_stream(self, response) -> Generator[str, None, None]:
        """处理流式响应"""
        full_content = ""
        
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data = line_text[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_content += content
                                yield content
                    except json.JSONDecodeError:
                        continue
        
        # 将完整回复添加到历史记录
        if full_content:
            self.conversation_history.append({
                "role": "assistant",
                "content": full_content
            })
    
    def _handle_stream_with_memory(self, response, original_message: str) -> Generator[str, None, None]:
        """处理流式响应并记录到记忆系统"""
        full_content = ""
        
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data = line_text[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_content += content
                                yield content
                    except json.JSONDecodeError:
                        continue
        
        # 将完整回复添加到历史记录
        if full_content:
            self.conversation_history.append({
                "role": "assistant",
                "content": full_content
            })
            # 记录到会话记忆
            self.memory.log_interaction(original_message, full_content)

    def clear_history(self):
        """清空对话历史（保留长期记忆）"""
        self.conversation_history = []
        self.memory.clear_session_memory()
    
    def get_history(self) -> list:
        """获取对话历史"""
        return self.conversation_history.copy()


if __name__ == "__main__":
    # 测试代码
    API_KEY = "sk-cp-R5mBFqj9u1T2bGt0aoKbmeND4g192tPUl-CQ5jLt4cbv5dsCSkmYbEVyfPALPzEI-jnVNfSQB_dHCAiiAO_pi2um_sWwFBbageq9P8yKmBc-ZaZeX7dY5Do"
    
    agent = MiniMaxAgent(API_KEY)
    
    print("=" * 60)
    print("🎓 MiniMax Agent - 教师辅助 AI 助手")
    print("=" * 60)
    print("通用指令:")
    print("  输入 'quit' 退出")
    print("  输入 'clear' 清空历史")
    print("-" * 60)
    print("PPT 功能:")
    print("  制作PPT：主题  - 生成演示文稿")
    print("  预览PPT        - 查看 PPT 内容")
    print("  列出PPT        - 查看所有 PPT 文件")
    print("-" * 60)
    print("讲义功能:")
    print("  生成讲义：主题  - 生成课程讲义(Markdown)")
    print("  列出讲义        - 查看所有讲义文件")
    print("=" * 60)
    
    while True:
        user_input = input("\n你: ").strip()
        
        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'clear':
            agent.clear_history()
            print("历史已清空")
            continue
        
        if not user_input:
            continue
        
        print("\nAI: ", end="", flush=True)
        response = agent.chat(user_input, stream=True)
        
        if isinstance(response, Generator):
            for chunk in response:
                print(chunk, end="", flush=True)
            print()
        else:
            print(response)
