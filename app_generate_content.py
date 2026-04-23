import re

@app.route('/api/generate/<module>', methods=['POST'])
def generate_content(module):
    """统一的内容生成接口（非流式），返回JSON含文件路径"""
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        course_info = data.get('course_info', {})

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if module == 'lecture-documentation':
            # 讲义文档
            prompt = lecture_generator.generate_lecture_prompt(topic)
            response = requests.post(
                f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                headers={
                    'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=120
            )
            result = response.json()['choices'][0]['message']['content']
            output_path = os.path.join(base_dir, 'generated_lectures', f'lecture_doc_{timestamp}.md')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            return jsonify({
                'success': True,
                'file': os.path.basename(output_path),
                'path': output_path,
                'url': f'/api/lectures/{os.path.basename(output_path)}',
                'content': result
            })

        elif module == 'lecture-notes':
            # 讲稿
            prompt = lecture_generator.generate_lecture_notes_prompt(topic)
            response = requests.post(
                f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                headers={
                    'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=120
            )
            result = response.json()['choices'][0]['message']['content']
            output_path = os.path.join(base_dir, 'generated_lectures', f'lecture_notes_{timestamp}.md')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            return jsonify({
                'success': True,
                'file': os.path.basename(output_path),
                'path': output_path,
                'url': f'/api/lectures/{os.path.basename(output_path)}',
                'content': result
            })

        elif module == 'xiaohongshu':
            # 小红书文案 + 封面图
            # 生成文案
            prompt = content_generator.generate_xiaohongshu_prompt(topic)
            response = requests.post(
                f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                headers={
                    'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=120
            )
            text_result = response.json()['choices'][0]['message']['content']

            # 保存文案
            text_path = os.path.join(base_dir, 'generated_content', 'text', f'xiaohongshu_{timestamp}.md')
            os.makedirs(os.path.dirname(text_path), exist_ok=True)
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_result)

            # 生成封面图
            image_path = None
            image_url = None
            try:
                cover_prompt = content_generator.generate_cover_image_prompt(topic)
                img_response = requests.post(
                    f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'deepseek-chat',
                        'messages': [{'role': 'user', 'content': cover_prompt}]
                    },
                    timeout=120
                )
                img_url = img_response.json()['choices'][0]['message']['content']
                if img_url.startswith('http'):
                    img_data = requests.get(img_url, timeout=30).content
                    image_path = os.path.join(base_dir, 'generated_content', 'images', f'cover_{timestamp}.jpg')
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    with open(image_path, 'wb') as f:
                        f.write(img_data)
                    image_url = f'/api/graphic/image/{os.path.basename(image_path)}'
            except Exception as e:
                print(f'Image generation failed: {e}')

            return jsonify({
                'success': True,
                'file': os.path.basename(text_path),
                'path': text_path,
                'url': f'/api/files?path={text_path}',
                'content': text_result,
                'image_path': image_path,
                'image_url': image_url
            })

        elif module == 'wechat':
            # 公众号文章
            prompt = content_generator.generate_wechat_prompt(topic)
            response = requests.post(
                f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                headers={
                    'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=120
            )
            result = response.json()['choices'][0]['message']['content']
            output_path = os.path.join(base_dir, 'generated_content', 'text', f'wechat_{timestamp}.md')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            return jsonify({
                'success': True,
                'file': os.path.basename(output_path),
                'path': output_path,
                'url': f'/api/files?path={output_path}',
                'content': result
            })

        elif module == 'content_image':
            # 图文封面图
            image_path = None
            image_url = None
            try:
                cover_prompt = content_generator.generate_cover_image_prompt(topic)
                img_response = requests.post(
                    f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'deepseek-chat',
                        'messages': [{'role': 'user', 'content': cover_prompt}]
                    },
                    timeout=120
                )
                img_url = img_response.json()['choices'][0]['message']['content']
                if img_url.startswith('http'):
                    img_data = requests.get(img_url, timeout=30).content
                    image_path = os.path.join(base_dir, 'generated_content', 'images', f'cover_{timestamp}.jpg')
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    with open(image_path, 'wb') as f:
                        f.write(img_data)
                    image_url = f'/api/graphic/image/{os.path.basename(image_path)}'
                    return jsonify({
                        'success': True,
                        'image_path': image_path,
                        'image_url': image_url
                    })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
            return jsonify({'success': False, 'error': 'Image generation failed'}), 500

        elif module == 'content_audio':
            # 音频配音
            # 调用Mimo API
            mimo_url = os.environ.get('MIMO_API_URL', '')
            mimo_key = os.environ.get('MIMO_API_KEY', '')
            if mimo_url and mimo_key:
                try:
                    audio_response = requests.post(
                        mimo_url,
                        headers={'Authorization': f'Bearer {mimo_key}'},
                        json={'text': topic, 'model': 'speech'},
                        timeout=60
                    )
                    audio_path = os.path.join(base_dir, 'generated_content', 'audio', f'audio_{timestamp}.wav')
                    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                    with open(audio_path, 'wb') as f:
                        f.write(audio_response.content)
                    return jsonify({
                        'success': True,
                        'audio_path': audio_path,
                        'audio_url': f'/api/video/audio/{os.path.basename(audio_path)}'
                    })
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)}), 500
            return jsonify({'success': False, 'error': 'Mimo API not configured'}), 500

        else:
            # 其他纯文本模块（homework, quiz, qa, knowledge-card, mind-map, etc.）
            # 这些模块只返回文本，不需要文件
            prompt_map = {
                'homework': content_generator.generate_homework_prompt,
                'quiz': content_generator.generate_quiz_prompt,
                'qa': content_generator.generate_qa_prompt,
                'knowledge-card': content_generator.generate_knowledge_card_prompt,
                'mind-map': content_generator.generate_mindmap_prompt,
                'short-video': content_generator.generate_short_video_prompt,
                'long-video': content_generator.generate_long_video_prompt,
                'script': content_generator.generate_script_prompt,
                'weibo': content_generator.generate_weibo_prompt,
                'douyin-intro': content_generator.generate_douyin_intro_prompt,
            }
            gen_func = prompt_map.get(module)
            if gen_func:
                prompt = gen_func(topic)
            else:
                prompt = f'请生成关于{topic}的内容'

            response = requests.post(
                f'{os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com')}/chat/completions',
                headers={
                    'Authorization': f'Bearer {os.environ.get("DEEPSEEK_API_KEY", "")}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=120
            )
            result = response.json()['choices'][0]['message']['content']
            return jsonify({
                'success': True,
                'content': result,
                'file': None,
                'path': None,
                'url': None
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
