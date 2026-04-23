"""
PPT 生成工具
为 MiniMax Agent 添加制作 PPT 的功能
"""

import json
import subprocess
import os
from typing import List, Dict, Optional
from datetime import datetime


class PPTGenerator:
    """PPT 生成器 - 使用 pptxgenjs 创建演示文稿"""
    
    def __init__(self, output_dir: str = "generated_ppt"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_ppt(self, title: str, slides_data: List[Dict], theme: str = "teal") -> str:
        """
        创建 PPT 文件
        
        Args:
            title: PPT 标题
            slides_data: 幻灯片内容列表
            theme: 主题颜色 (teal, coral, navy, forest, charcoal)
            
        Returns:
            生成的文件路径
        """
        # 定义主题配色
        themes = {
            "teal": {"primary": "028090", "secondary": "00A896", "accent": "02C39A", "bg": "FFFFFF", "text": "333333"},
            "coral": {"primary": "F96167", "secondary": "F9E795", "accent": "2F3C7E", "bg": "FFFFFF", "text": "333333"},
            "navy": {"primary": "1E2761", "secondary": "CADCFC", "accent": "FFFFFF", "bg": "FFFFFF", "text": "1E2761"},
            "forest": {"primary": "2C5F2D", "secondary": "97BC62", "accent": "F5F5F5", "bg": "FFFFFF", "text": "2C5F2D"},
            "charcoal": {"primary": "36454F", "secondary": "F2F2F2", "accent": "212121", "bg": "FFFFFF", "text": "36454F"},
        }
        
        color = themes.get(theme, themes["teal"])
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.pptx"
        output_path = os.path.join(self.output_dir, filename)
        
        # 构建 pptxgenjs 脚本
        pptx_script = self._build_pptx_script(title, slides_data, color, output_path)
        
        # 保存临时 JS 文件
        js_file = os.path.join(self.output_dir, f"temp_{timestamp}.js")
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(pptx_script)
        
        try:
            # 执行 Node.js 脚本（从项目根目录运行，以便找到 node_modules）
            project_root = os.path.dirname(os.path.abspath(__file__))
            result = subprocess.run(
                ['node', js_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=30,
                cwd=project_root  # 从项目根目录运行
            )
            
            if result.returncode != 0:
                raise Exception(f"PPT 生成失败: {result.stderr}")
            
            # 删除临时 JS 文件
            os.remove(js_file)
            
            return output_path
            
        except Exception as e:
            if os.path.exists(js_file):
                os.remove(js_file)
            raise e
    
    def _build_pptx_script(self, title: str, slides_data: List[Dict], color: Dict, output_path: str) -> str:
        """构建 pptxgenjs JavaScript 代码"""
        
        slides_js = []
        
        for i, slide in enumerate(slides_data):
            slide_type = slide.get('type', 'content')
            slide_title = slide.get('title', '')
            content = slide.get('content', [])
            
            if slide_type == 'title':
                # 标题页
                slides_js.append(f'''
    // 标题页
    slide = pptx.addSlide();
    slide.background = {{ color: "{color['primary']}" }};
    slide.addText("{self._escape_js(slide_title)}", {{
        x: 0.5, y: 2.5, w: 9, h: 1.5,
        fontSize: 44, bold: true, color: "FFFFFF", align: "center"
    }});
''')
            
            elif slide_type == 'content':
                # 内容页
                content_text = []
                for item in content:
                    if isinstance(item, dict):
                        text = item.get('text', '')
                        level = item.get('level', 0)
                        indent = "  " * level
                        content_text.append(f"{indent}• {self._escape_js(text)}")
                    else:
                        content_text.append(f"• {self._escape_js(str(item))}")
                
                content_str = "\\n".join(content_text)
                
                slides_js.append(f'''
    // 内容页 {i+1}
    slide = pptx.addSlide();
    slide.addText("{self._escape_js(slide_title)}", {{
        x: 0.5, y: 0.5, w: 9, h: 0.8,
        fontSize: 32, bold: true, color: "{color['primary']}"
    }});
    slide.addText("{content_str}", {{
        x: 0.5, y: 1.5, w: 9, h: 5,
        fontSize: 18, color: "{color['text']}",
        bullet: false, lineSpacing: 30
    }});
''')
            
            elif slide_type == 'section':
                # 章节页
                slides_js.append(f'''
    // 章节页
    slide = pptx.addSlide();
    slide.background = {{ color: "{color['secondary']}" }};
    slide.addText("{self._escape_js(slide_title)}", {{
        x: 0.5, y: 2.5, w: 9, h: 1.5,
        fontSize: 40, bold: true, color: "{color['primary']}", align: "center"
    }});
''')
        
        # 完整的 JS 脚本
        script = f'''const PptxGenJS = require("pptxgenjs");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_16x9";
pptx.title = "{self._escape_js(title)}";
pptx.author = "MiniMax Agent";

let slide;
{''.join(slides_js)}

pptx.writeFile({{ fileName: "{output_path.replace('\\', '/')}" }})
    .then(() => console.log("PPT 生成成功: {output_path}"))
    .catch(err => {{ console.error("错误:", err); process.exit(1); }});
'''
        return script
    
    def _escape_js(self, text: str) -> str:
        """转义 JavaScript 字符串"""
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    
    def parse_ppt_request(self, user_input: str) -> Optional[Dict]:
        """
        解析用户的 PPT 制作请求
        
        支持的指令格式：
        - "制作PPT：主题"
        - "生成PPT：主题"
        - "创建PPT：主题"
        - "帮我做PPT：主题"
        """
        import re
        
        patterns = [
            r'(?:制作|生成|创建|做|写).*?[Pp][Pp][Tt].*?[:：]\s*(.+)',
            r'帮我.*?[Pp][Pp][Tt].*?[:：]\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                topic = match.group(1).strip()
                return {
                    'action': 'create_ppt',
                    'topic': topic
                }
        
        return None


# 测试代码
if __name__ == "__main__":
    generator = PPTGenerator()
    
    # 测试数据
    test_slides = [
        {"type": "title", "title": "人工智能简介"},
        {"type": "content", "title": "什么是人工智能", "content": [
            {"text": "人工智能是计算机科学的一个分支", "level": 0},
            {"text": "致力于创造能够模拟人类智能的系统", "level": 0},
            {"text": "包括学习、推理、感知等功能", "level": 0},
        ]},
        {"type": "content", "title": "AI 的应用领域", "content": [
            {"text": "机器学习", "level": 0},
            {"text": "深度学习", "level": 0},
            {"text": "自然语言处理", "level": 0},
            {"text": "计算机视觉", "level": 0},
        ]},
        {"type": "section", "title": "谢谢观看"},
    ]
    
    try:
        output = generator.create_ppt("人工智能简介", test_slides, theme="teal")
        print(f"PPT 已生成: {output}")
    except Exception as e:
        print(f"生成失败: {e}")
