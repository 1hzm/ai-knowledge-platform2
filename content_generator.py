"""
自媒体内容生成器
将专业知识转化为社交媒体爆款内容
支持：短视频脚本、小红书文案、TTS音频、AI封面图
"""

import os
import re
import json
import base64
import time
import requests
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Generator
import logging

# 配置日志
logger = logging.getLogger('MiniMaxAgent.content')


class ContentGenerator:
    """自媒体内容生成器"""

    # API 配置 - 沿用原有设计，硬编码
    DEEPSEEK_API_KEY = "sk-d95d1b8567d844889648d0bda30a8ebe"  # 请替换为你的 key
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    DEEPSEEK_MODEL = "deepseek-chat"

    MIMO_API_KEY = "sk-cf3y8ftjor9awrff2kt3ni9ijolrj0zjx4vp8rz5250hfxac"  # 请替换为你的 key
    MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
    MIMO_MODEL = "mimo-v2-tts"
    MIMO_VOICE = "mimo_default"

    MINIMAX_IMAGE_API_KEY = "sk-api-qGS9gpTGTTLYCAd3Z2tC_AX5yEfX18DxLxN7OvsijebsnRo2FxwNbE-gSMim_ueJleRew7hD9rv0wrniIPgy84pFTmfGLbwIZcd5-CwXQMhm7Dh5iaRJhgk"  # 请替换为你的 key

    # 默认设置
    DEFAULT_SETTINGS = {
        'mimo_voice': 'mimo_default',
        'mimo_style': '',
        'aspect_ratio': '3:4',
        'cover_style': 'infographic'
    }

    def __init__(self, output_dir: str = "generated_content", settings: dict = None):
        self.output_dir = output_dir
        self.audio_dir = os.path.join(output_dir, "audio")
        self.image_dir = os.path.join(output_dir, "images")
        self.text_dir = os.path.join(output_dir, "text")

        # 创建输出目录
        for dir_path in [self.audio_dir, self.image_dir, self.text_dir]:
            os.makedirs(dir_path, exist_ok=True)

        # 应用设置（使用默认值覆盖）
        self.settings = {**self.DEFAULT_SETTINGS, **(settings or {})}

        logger.info(f"ContentGenerator initialized, output dir: {output_dir}, settings: {self.settings}")

    def update_settings(self, settings: dict):
        """更新设置"""
        self.settings.update(settings)
        logger.info(f"Settings updated: {self.settings}")

    def parse_content_request(self, message: str) -> Optional[Dict]:
        """
        解析内容生成请求

        支持的格式：
        - 生成图文：主题  -> 生成小红书文案+封面图
        - 短视频：主题    -> 生成短视频脚本+AI配音
        """
        # 图文内容（小红书风格）
        graphic_patterns = [
            r'(?:生成|创作|制作).*?图文[：:]\s*(.+)',
            r'(?:生成|创作|制作).*?小红书[：:]\s*(.+)',
        ]
        for pattern in graphic_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return {
                    'topic': match.group(1).strip(),
                    'type': 'graphic_content'  # 图文内容
                }

        # 短视频脚本
        video_patterns = [
            r'(?:生成|创作|制作|短视频)[：:]\s*(.+)',
        ]
        for pattern in video_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return {
                    'topic': match.group(1).strip(),
                    'type': 'video_script'  # 短视频脚本
                }

        return None

    def generate_graphic_content_stream(self, topic: str) -> Generator[Dict, None, None]:
        """
        流式生成图文内容（小红书文案 + 封面图）
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 用于保存生成的数据，最终在 complete 步骤返回
            result_data = {
                'text_file': '',
                'xiaohongshu': '',
                'image_path': '',
                'image_base64': '',
                'prompt': ''
            }

            # Step 1: 开始
            yield {
                'step': 'start',
                'progress': 0,
                'status': 'running',
                'data': {},
                'message': '🚀 开始生成图文内容...'
            }

            # Step 2: 生成小红书文案
            yield {
                'step': 'generate_text',
                'progress': 20,
                'status': 'running',
                'data': {},
                'message': '📝 正在生成小红书爆款文案...'
            }

            xiaohongshu_content = self._generate_xiaohongshu_content(topic)
            result_data['xiaohongshu'] = xiaohongshu_content

            # 保存文本内容
            text_filename = f"xiaohongshu_{timestamp}.md"
            text_path = os.path.join(self.text_dir, text_filename)

            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(f"# 小红书文案\n\n{xiaohongshu_content}\n")

            result_data['text_file'] = text_path

            yield {
                'step': 'text_complete',
                'progress': 50,
                'status': 'running',
                'data': {
                    'xiaohongshu': xiaohongshu_content,
                    'text_file': text_path
                },
                'message': '✅ 文案生成完成！正在生成封面图...'
            }

            # Step 3: 生成封面图
            yield {
                'step': 'generate_image',
                'progress': 70,
                'status': 'running',
                'data': {},
                'message': '🎨 正在生成 AI 封面图...'
            }

            try:
                cover_style = self.settings.get('cover_style', 'infographic')
                image_prompt = self._generate_image_prompt(xiaohongshu_content, cover_style)
                aspect_ratio = self.settings.get('aspect_ratio', '3:4')
                image_bytes = self._generate_cover_image(image_prompt, aspect_ratio)

                image_filename = f"cover_{timestamp}.jpeg"
                image_path = os.path.join(self.image_dir, image_filename)

                with open(image_path, 'wb') as f:
                    f.write(image_bytes)

                # 转换为 base64 供前端显示
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                image_base64_url = f"data:image/jpeg;base64,{image_base64}"

                result_data['image_path'] = image_path
                result_data['image_base64'] = image_base64_url
                result_data['prompt'] = image_prompt

                # 先发送封面图片数据（单独发送，避免 complete 消息过大）
                yield {
                    'step': 'image_data',
                    'progress': 85,
                    'status': 'running',
                    'data': {
                        'type': 'graphic_image_data',
                        'image_base64': image_base64_url,
                        'prompt': image_prompt
                    },
                    'message': '🎨 封面图片已生成'
                }

                yield {
                    'step': 'image_complete',
                    'progress': 90,
                    'status': 'running',
                    'data': {
                        'image_path': image_path,
                        'prompt': image_prompt
                    },
                    'message': '✅ 封面生成完成！'
                }
            except Exception as e:
                logger.error(f"Image generation failed: {e}")
                yield {
                    'step': 'image_error',
                    'progress': 90,
                    'status': 'running',
                    'data': {'error': str(e)},
                    'message': f'⚠️ 封面生成失败: {e}'
                }

            # Step 4: 完成
            yield {
                'step': 'complete',
                'progress': 100,
                'status': 'completed',
                'data': result_data,
                'message': '🎉 图文内容生成完成！'
            }

        except Exception as e:
            logger.error(f"Graphic content generation failed: {e}")
            yield {
                'step': 'error',
                'progress': 0,
                'status': 'error',
                'data': {'error': str(e)},
                'message': f'❌ 生成失败: {e}'
            }

    def generate_video_script_stream(self, topic: str, style: str = "") -> Generator[Dict, None, None]:
        """
        流式生成短视频脚本（脚本 + AI配音）
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 用于保存生成的数据，最终在 complete 步骤返回
            result_data = {
                'text_file': '',
                'video_script': '',
                'audio_path': '',
                'audio_base64': '',
                'voiceover_text': ''
            }

            # Step 1: 开始
            yield {
                'step': 'start',
                'progress': 0,
                'status': 'running',
                'data': {},
                'message': '🚀 开始生成短视频脚本...'
            }

            # Step 2: 生成短视频脚本
            yield {
                'step': 'generate_script',
                'progress': 20,
                'status': 'running',
                'data': {},
                'message': '📝 正在生成短视频脚本...'
            }

            video_script = self._generate_short_video_script(topic)
            result_data['video_script'] = video_script

            # 保存文本内容
            text_filename = f"video_script_{timestamp}.md"
            text_path = os.path.join(self.text_dir, text_filename)

            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(f"# 短视频脚本\n\n{video_script}\n")

            result_data['text_file'] = text_path

            yield {
                'step': 'script_complete',
                'progress': 50,
                'status': 'running',
                'data': {
                    'video_script': video_script,
                    'text_file': text_path
                },
                'message': '✅ 脚本生成完成！正在合成 AI 配音...'
            }

            # Step 3: 生成语音
            yield {
                'step': 'generate_audio',
                'progress': 60,
                'status': 'running',
                'data': {},
                'message': '🔊 正在合成 AI 语音...'
            }

            try:
                voiceover = self._extract_voiceover(video_script)
                audio_bytes = self._generate_mimo_audio(voiceover, style)

                audio_filename = f"voice_{timestamp}.wav"
                audio_path = os.path.join(self.audio_dir, audio_filename)

                with open(audio_path, 'wb') as f:
                    f.write(audio_bytes)

                # 转换为 base64 供前端播放
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                audio_base64_url = f"data:audio/wav;base64,{audio_base64}"

                result_data['audio_path'] = audio_path
                result_data['audio_base64'] = audio_base64_url
                result_data['voiceover_text'] = voiceover

                # 先发送音频数据（单独发送，避免 complete 消息过大）
                yield {
                    'step': 'audio_data',
                    'progress': 85,
                    'status': 'running',
                    'data': {
                        'type': 'video_audio_data',
                        'audio_base64': audio_base64_url,
                        'voiceover_text': voiceover
                    },
                    'message': '🔊 音频已合成'
                }

                yield {
                    'step': 'audio_complete',
                    'progress': 90,
                    'status': 'running',
                    'data': {
                        'audio_path': audio_path,
                        'voiceover_text': voiceover
                    },
                    'message': '✅ 语音合成完成！'
                }
            except Exception as e:
                logger.error(f"Audio generation failed: {e}")
                yield {
                    'step': 'audio_error',
                    'progress': 90,
                    'status': 'running',
                    'data': {'error': str(e)},
                    'message': f'⚠️ 语音生成失败: {e}'
                }

            # Step 4: 完成
            yield {
                'step': 'complete',
                'progress': 100,
                'status': 'completed',
                'data': result_data,
                'message': '🎉 短视频脚本生成完成！'
            }

        except Exception as e:
            logger.error(f"Video script generation failed: {e}")
            yield {
                'step': 'error',
                'progress': 0,
                'status': 'error',
                'data': {'error': str(e)},
                'message': f'❌ 生成失败: {e}'
            }

    # ========== 以下方法保持原有设计不变 ==========

    def _call_llm(self, prompt: str, system_msg: str = "你是一个专业的内容创作专家") -> str:
        """调用大语言模型 API - 保持原有设计"""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.DEEPSEEK_API_KEY,
            base_url=self.DEEPSEEK_BASE_URL
        )

        response = client.chat.completions.create(
            model=self.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        return response.choices[0].message.content

    def _generate_short_video_script(self, knowledge: str) -> str:
        """生成短视频脚本 - 保持原有设计"""
        prompt = f"""
请将以下专业知识转化为一个吸引人的短视频脚本（时长60-90秒）。

原始知识内容：
{knowledge}

请按以下结构输出：

📌 **开头吸引点（黄金3秒）**：
- 用悬念/冲突/反常识的方式开场，让观众停下刷视频的手指

📌 **核心干货内容（中间30-50秒）**：
- 用"人话"拆解复杂概念
- 使用类比、故事或案例让知识通俗易懂
- 分2-3个要点呈现

📌 **行动呼吁（结尾10秒）**：
- 引导点赞/收藏/关注
- 或提出一个互动问题

📌 **画面描述建议**：
- 每个段落配什么画面/动画/文字特效
"""
        return self._call_llm(prompt, "你是抖音/B站爆款短视频编剧专家")

    def _generate_xiaohongshu_content(self, knowledge: str) -> str:
        """生成小红书文案 - 保持原有设计"""
        prompt = f"""
请将以下专业知识转化为小红书风格的爆款笔记。

原始知识内容：
{knowledge}

请按以下结构输出：

📌 **高点击率标题**（提供3个选项）：
- 带emoji，使用数字/悬念/痛点/利益点
- 控制在20字以内

📌 **结构化正文**：
- 开头：痛点共鸣或惊人发现（2-3行）
- 正文：分点叙述，每点带emoji图标
- 使用"姐妹们"、"家人们"等小红书口吻
- 适当使用"绝了"、"挖到宝了"、"后悔没早点"等表达

📌 **相关话题标签**（8-10个）：
- 包含热门标签和精准标签
- 格式如 #知识分享 #自我提升 等

📌 **封面图建议**：
- 标题文字排版建议
- 配色/字体风格
"""
        return self._call_llm(prompt, "你是小红书10万粉博主，擅长写爆款种草笔记")

    def _extract_voiceover(self, script: str) -> str:
        """从短视频脚本中提取纯净旁白文本 - 保持原有设计"""
        prompt = f"""
请从以下短视频脚本中提取出适合朗读的纯净旁白文本。

要求：
1. 剔除所有画面描述、动作指令、转场说明等非口播内容
2. 剔除所有标题标记（如"开头吸引点"、"核心干货内容"等）
3. 仅保留主播需要朗读的台词内容
4. 保持语句通顺连贯
5. 输出为一整段纯文本，不需要任何格式标记

原始脚本：
{script}

请直接输出旁白文本：
"""
        return self._call_llm(prompt, "你是一个专业的视频编导，擅长提取脚本旁白")

    def _generate_mimo_audio(self, voiceover_text: str, style: str = "") -> bytes:
        """调用 MiMo V2-TTS 生成音频 - 保持原有设计"""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.MIMO_API_KEY,
            base_url=self.MIMO_BASE_URL
        )

        # 添加风格标签到文本开头
        if style:
            voiceover_text = f"<style>{style}</style>{voiceover_text}"

        response = client.chat.completions.create(
            model=self.MIMO_MODEL,
            messages=[
                {"role": "user", "content": "请朗读以下内容"},
                {"role": "assistant", "content": voiceover_text}
            ],
            audio={
                "format": "wav",
                "voice": self.settings.get('mimo_voice', 'mimo_default')
            }
        )

        # 从响应中获取 Base64 编码的音频数据
        audio_data = response.choices[0].message.audio.data
        # 解码为二进制数据
        audio_bytes = base64.b64decode(audio_data)

        return audio_bytes

    def _generate_image_prompt(self, xiaohongshu_content: str, style: str = "infographic") -> str:
        """根据小红书文案生成封面描述词 - 支持多种风格"""

        if style == "minimal":
            # 极简纯图版风格
            prompt = f"""
请根据以下小红书文案内容，生成一段适合 AI 图像生成的英文视觉描述词。

要求：
1. 真实摄影感风格，画面简洁高级
2. 极简主义设计，突出核心主题
3. 包含核心关键词，避免复杂文字
4. 适合社交媒体封面，有视觉冲击力
5. 仅输出英文描述词，不超过50个词

小红书文案：
{xiaohongshu_content}

请直接输出英文图像描述词：
"""
            system_msg = "你是一位专业的视觉设计师，擅长用简洁的英文描述创作高质量图像"
        else:
            # 一图流文字版风格（默认）
            prompt = f"""
请根据以下小红书内容，生成一段适合 AI 图像生成的英文视觉描述词。

要求：
1. 信息图/一图流风格，画面包含清晰可读的大标题文字
2. 现代扁平化设计，配色高级（莫兰迪色系或明亮渐变色）
3. 标题醒目居中，字体粗大易读
4. 背景与主题相关，有视觉层次
5. 小红书风格，适合知识分享类笔记封面
6. 英文描述，包含 "infographic style, bold typography, clean layout, text overlay, social media cover"

小红书文案：
{xiaohongshu_content}

请直接输出英文图像描述词（60-80词）：
"""
            system_msg = "你是一位专业的社交媒体视觉设计师，擅长设计小红书爆款信息图封面"

        return self._call_llm(prompt, system_msg)

    def _generate_cover_image(self, prompt: str, aspect_ratio: str = "3:4") -> bytes:
        """调用 MiniMax 生成封面图"""
        url = "https://api.minimaxi.com/v1/image_generation"
        headers = {"Authorization": f"Bearer {self.MINIMAX_IMAGE_API_KEY}"}
        payload = {
            "model": "image-01",
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "response_format": "base64"
        }

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Image API response: {data}")

        # 先检查 API 错误状态
        if isinstance(data, dict) and "base_resp" in data:
            base_resp = data["base_resp"]
            status_code = base_resp.get("status_code", 0) if isinstance(base_resp, dict) else 0
            status_msg = base_resp.get("status_msg", "") if isinstance(base_resp, dict) else ""
            if status_code != 0:
                raise ValueError(f"图片生成 API 错误 ({status_code}): {status_msg}")

        # 兼容多种响应格式
        images = None
        if isinstance(data, dict):
            # 尝试 data.data.image_base64 格式
            if "data" in data and isinstance(data["data"], dict):
                images = data["data"].get("image_base64")
            # 尝试 data.data[0].image_base64 格式
            elif "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                images = data["data"][0].get("image_base64") if isinstance(data["data"][0], dict) else None
            # 直接 image_base64 格式
            elif "image_base64" in data:
                images = data.get("image_base64")

        if not images:
            raise ValueError(f"未返回图像数据: {data}")

        return base64.b64decode(images[0] if isinstance(images, list) else images)

    def list_generated_content(self) -> List[Dict]:
        """列出所有生成的内容"""
        contents = []

        # 扫描文本文件
        if os.path.exists(self.text_dir):
            for f in os.listdir(self.text_dir):
                if f.endswith('.md'):
                    filepath = os.path.join(self.text_dir, f)
                    stat = os.stat(filepath)
                    contents.append({
                        'filename': f,
                        'path': filepath,
                        'type': 'text',
                        'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'size': stat.st_size
                    })

        # 扫描音频文件
        if os.path.exists(self.audio_dir):
            for f in os.listdir(self.audio_dir):
                if f.endswith('.wav'):
                    filepath = os.path.join(self.audio_dir, f)
                    stat = os.stat(filepath)
                    contents.append({
                        'filename': f,
                        'path': filepath,
                        'type': 'audio',
                        'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'size': stat.st_size
                    })

        # 扫描图片文件
        if os.path.exists(self.image_dir):
            for f in os.listdir(self.image_dir):
                if f.endswith(('.jpeg', '.jpg', '.png')):
                    filepath = os.path.join(self.image_dir, f)
                    stat = os.stat(filepath)
                    contents.append({
                        'filename': f,
                        'path': filepath,
                        'type': 'image',
                        'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'size': stat.st_size
                    })

        # 按时间倒序排列
        contents.sort(key=lambda x: x['created'], reverse=True)
        return contents


if __name__ == "__main__":
    # 测试代码
    generator = ContentGenerator()
    print("内容生成器测试")

    test_knowledge = """费曼学习法是一种高效的学习方法，由诺贝尔物理学奖得主理查德·费曼提出。"""

    for update in generator.generate_content_stream(test_knowledge):
        print(f"[{update['progress']}%] {update['message']}")
