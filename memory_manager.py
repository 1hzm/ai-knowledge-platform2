"""
记忆管理系统 - MiniMax Agent 的记忆系统
参考 OpenClaw 的记忆设计，支持永久记忆和会话记忆
"""

import os
import json
from datetime import datetime
from typing import Optional


class MemoryManager:
    """记忆管理器"""

    def __init__(self, base_dir: str = None, session_id: str = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.base_dir = base_dir
        self.memory_dir = os.path.join(base_dir, 'memory')
        self.session_dir = os.path.join(self.memory_dir, 'sessions')
        self.memory_file = os.path.join(self.memory_dir, 'MEMORY.md')
        self.config_file = os.path.join(self.memory_dir, 'config.json')

        # 会话 ID（用于隔离会话记录）
        self.session_id = session_id or "default"

        # 确保目录存在
        os.makedirs(self.session_dir, exist_ok=True)

        # 初始化配置文件
        if not os.path.exists(self.config_file):
            self._init_config()

        # 加载长期记忆
        self.long_term_memory = self._load_long_term_memory()

        # 当前会话记忆（内存）
        self.session_memory = {}
    
    def _init_config(self):
        """初始化配置文件"""
        config = {
            "user_name": "",
            "preferences": {},
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def _load_long_term_memory(self) -> str:
        """加载长期记忆"""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def _save_long_term_memory(self, content: str):
        """保存长期记忆"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _get_session_file(self) -> str:
        """获取当前会话的记录文件路径"""
        return os.path.join(self.session_dir, f"{self.session_id}.md")

    def load_session_memory(self) -> str:
        """加载当前会话的记录"""
        session_file = self._get_session_file()
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def save_session_memory(self, content: str):
        """保存到当前会话记录"""
        session_file = self._get_session_file()
        with open(session_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def append_to_session(self, entry: str):
        """
        添加会话记录条目
        entry 格式：## HH:MM\n内容\n
        """
        session_file = self._get_session_file()
        session_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 如果文件不存在，先创建标题
        if not os.path.exists(session_file):
            header = f"# 会话记录 - {session_start}\n\n"
        else:
            header = ""

        time_str = datetime.now().strftime("%H:%M:%S")
        entry_text = f"{header}## {time_str}\n{entry}\n\n"

        with open(session_file, 'a', encoding='utf-8') as f:
            f.write(entry_text)

    def clear_session_file(self):
        """清除当前会话记录文件"""
        session_file = self._get_session_file()
        if os.path.exists(session_file):
            os.remove(session_file)
    
    def get_context_for_prompt(self) -> str:
        """
        获取注入到 AI prompt 的上下文记忆
        """
        parts = []
        
        # 0. 系统提示（告诉 AI 这是它的长期记忆）
        system_note = "【重要】以下是你的长期记忆库，当用户询问相关问题或需要用到这些知识时，你应该主动引用它们。"
        parts.append(system_note)
        
        # 1. 长期记忆（如果存在）
        if self.long_term_memory.strip():
            parts.append("【长期记忆】")
            parts.append(self.long_term_memory.strip())
        
        # 2. 用户偏好（从配置文件）
        config = self.get_config()
        if config.get('user_name'):
            parts.append(f"【用户信息】用户名称：{config['user_name']}")
        
        if config.get('preferences'):
            parts.append(f"【偏好设置】{json.dumps(config['preferences'], ensure_ascii=False)}")
        
        # 3. 当前会话记录（注入 AI 上下文，让 AI 知道本会话对话历史）
        session_memory = self.load_session_memory()
        if session_memory.strip():
            # 截断过长的会话记录，避免超出 token 限制
            if len(session_memory) > 2000:
                parts.append("【当前对话记录】（最近内容）")
                parts.append(session_memory[-2000:])
            else:
                parts.append("【当前对话记录】")
                parts.append(session_memory)
        
        if not parts:
            return ""
        
        return "\n\n---\n【记忆系统】\n" + "\n\n".join(parts) + "\n【记忆系统结束】\n\n"
    
    def get_config(self) -> dict:
        """获取配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def update_config(self, updates: dict):
        """更新配置"""
        config = self.get_config()
        config.update(updates)
        config['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def set_user_name(self, name: str):
        """设置用户名"""
        self.update_config({"user_name": name})
    
    def set_preference(self, key: str, value):
        """设置单个偏好"""
        config = self.get_config()
        if 'preferences' not in config:
            config['preferences'] = {}
        config['preferences'][key] = value
        self.update_config(config)
    
    def upgrade_to_long_term(self, content: str):
        """
        将内容提升到长期记忆
        在已有记忆后追加
        """
        if self.long_term_memory.strip():
            new_memory = self.long_term_memory + "\n\n" + content
        else:
            new_memory = content
        self._save_long_term_memory(new_memory)
        self.long_term_memory = new_memory
    
    def clear_long_term_memory(self):
        """清除长期记忆"""
        self._save_long_term_memory("")
        self.long_term_memory = ""
    
    def set_session_memory(self, key: str, value):
        """设置会话记忆（非持久化）"""
        self.session_memory[key] = value
    
    def get_session_memory(self, key: str, default=None):
        """获取会话记忆"""
        return self.session_memory.get(key, default)
    
    def clear_session_memory(self):
        """清除会话记忆"""
        self.session_memory = {}
    
    def log_interaction(self, user_message: str, ai_response: str, context: str = ""):
        """
        记录一次对话交互到会话记忆
        """
        today = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M:%S")

        entry = f"""## 对话记录 - {time_str}

**用户**: {user_message[:200]}{'...' if len(user_message) > 200 else ''}

**AI**: {ai_response[:500]}{'...' if len(ai_response) > 500 else ''}
{f'\n**场景**: {context}' if context else ''}
"""
        self.append_to_session(entry)

    def log_generation(self, topic: str, generation_type: str, result_data: dict):
        """
        记录生成任务完成到会话记忆

        Args:
            topic: 生成主题
            generation_type: 'ppt' | 'lecture' | 'graphic_content' | 'video_script'
            result_data: 包含文件路径、时间戳等元数据的字典
        """
        time_str = datetime.now().strftime("%H:%M:%S")

        # 过滤掉 base64 等大数据，只保留文件路径等元数据
        metadata = {k: v for k, v in result_data.items()
                    if 'base64' not in k and 'audio_base64' not in k and 'image_base64' not in k}

        # 格式化大纲文本
        outline_text = ""
        if generation_type == 'ppt' and 'slides' in metadata:
            slides = metadata['slides']
            outline_text = "\n\n**PPT大纲**:\n"
            for i, slide in enumerate(slides):
                slide_type = slide.get('type', 'content')
                slide_title = slide.get('title', f'第{i+1}页')
                if slide_type == 'title':
                    outline_text += f"  🎬 封面：{slide_title}\n"
                elif slide_type == 'section':
                    outline_text += f"  📑 章节：{slide_title}\n"
                else:
                    outline_text += f"  📄 {slide_title}\n"
                    content = slide.get('content', [])
                    if content:
                        for item in content:
                            if isinstance(item, dict):
                                outline_text += f"     • {item.get('text', '')}\n"
                            else:
                                outline_text += f"     • {item}\n"
            del metadata['slides']  # 从 metadata 中移除，避免重复

        elif generation_type == 'lecture' and 'lecture_content' in metadata:
            # 讲义内容：保存前500字作为草稿
            lecture_content = metadata['lecture_content']
            if len(lecture_content) > 500:
                outline_text = f"\n\n**讲义草稿**（前500字）:\n{lecture_content[:500]}\n..."
            else:
                outline_text = f"\n\n**讲义草稿**:\n{lecture_content}\n"
            del metadata['lecture_content']  # 从 metadata 中移除

        elif generation_type == 'graphic_content' and 'xiaohongshu' in metadata:
            # 图文内容：保存小红书文案前300字
            xiaohongshu = metadata['xiaohongshu']
            if len(xiaohongshu) > 300:
                outline_text = f"\n\n**图文文案**（前300字）:\n{xiaohongshu[:300]}\n..."
            else:
                outline_text = f"\n\n**图文文案**:\n{xiaohongshu}\n"
            del metadata['xiaohongshu']

        elif generation_type == 'video_script' and 'video_script' in metadata:
            # 视频脚本：保存脚本前500字
            script = metadata['video_script']
            if len(script) > 500:
                outline_text = f"\n\n**视频脚本**（前500字）:\n{script[:500]}\n..."
            else:
                outline_text = f"\n\n**视频脚本**:\n{script}\n"
            del metadata['video_script']

        entry = f"""## 生成记录 - {time_str}

**类型**: {generation_type}
**主题**: {topic}
{outline_text}
**元数据**: {json.dumps(metadata, ensure_ascii=False, indent=2)}
"""
        self.append_to_session(entry)
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要（用于查看）"""
        import re
        lines = ["📝 记忆摘要", "=" * 40]

        if self.long_term_memory.strip():
            lines.append("\n【长期记忆】")
            # 用 【 作为分隔符拆分所有条目
            parts = re.split(r'(?=【)', self.long_term_memory.strip())

            type_map = {
                'ppt': '📊 PPT',
                'lecture': '📚 讲义',
                'graphic_content': '📕 图文',
                'video_script': '🎬 视频脚本',
                '对话': '💬 对话'
            }

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                # 获取类型（【】中的内容）
                type_match = re.match(r'【([^】]+)】', part)
                if not type_match:
                    continue

                gen_type = type_match.group(1).lower()
                type_label = type_map.get(gen_type, gen_type)

                # 统一解析 **主题** 格式
                topic_match = re.search(r'\*\*主题\*\*[：:]\s*(.+?)(?:\n|$)', part)
                topic = topic_match.group(1).strip()[:50] if topic_match else "无主题"
                lines.append(f"  {type_label}：{topic}")

                lines.append("")

        else:
            lines.append("\n【长期记忆】（空）")

        # 用户配置
        config = self.get_config()
        if config.get('user_name'):
            lines.append(f"\n【用户】{config['user_name']}")

        # 当前会话记录
        session_mem = self.load_session_memory()
        if session_mem.strip():
            lines.append(f"\n【当前会话记录】（{len(session_mem)} 字符）")
        else:
            lines.append("\n【当前会话记录】（空）")

        return "\n".join(lines)

    def _extract_slide_titles(self, text: str) -> list:
        """从记忆文本中提取前3页标题"""
        import re
        pattern = r'[🎬📄📑]\s*([^：\n]+)'
        matches = re.findall(pattern, text)
        return [m.strip() for m in matches[:3]]

    def search_memory(self, keyword: str) -> list:
        """
        搜索记忆内容
        返回包含关键词的记忆片段
        """
        results = []
        
        # 搜索长期记忆
        if keyword.lower() in self.long_term_memory.lower():
            results.append({
                'source': '长期记忆',
                'content': self._find_context_around(self.long_term_memory, keyword)
            })
        
        # 搜索会话记录
        if os.path.exists(self.session_dir):
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.md'):
                    filepath = os.path.join(self.session_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if keyword.lower() in content.lower():
                            results.append({
                                'source': f'会话记录/{filename}',
                                'content': self._find_context_around(content, keyword)
                            })
        
        return results
    
    def _find_context_around(self, text: str, keyword: str, context_chars: int = 200) -> str:
        """找到关键词周围的上下文"""
        lower_text = text.lower()
        lower_keyword = keyword.lower()
        pos = lower_text.find(lower_keyword)
        
        if pos == -1:
            return ""
        
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(keyword) + context_chars)
        
        excerpt = text[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."
        
        return excerpt


# 便捷函数
def create_memory_manager(base_dir: str = None) -> MemoryManager:
    """创建记忆管理器实例"""
    return MemoryManager(base_dir)
