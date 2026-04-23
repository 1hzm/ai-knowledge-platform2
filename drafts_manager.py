"""
草稿箱管理器
存储课程草稿到文件系统
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional


class DraftsManager:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.drafts_dir = os.path.join(base_dir, 'drafts')
        os.makedirs(self.drafts_dir, exist_ok=True)

    def list(self) -> list:
        """列出所有草稿"""
        drafts = []
        if not os.path.exists(self.drafts_dir):
            return drafts
        for fname in os.listdir(self.drafts_dir):
            if fname.endswith('.json'):
                try:
                    with open(os.path.join(self.drafts_dir, fname), 'r', encoding='utf-8') as f:
                        drafts.append(json.load(f))
                except:
                    pass
        drafts.sort(key=lambda x: x.get('updatedAt', ''), reverse=True)
        return drafts

    def _get_file(self, draft_id: str) -> str:
        safe_id = ''.join(c for c in draft_id if c.isalnum() or c in '-_')
        return os.path.join(self.drafts_dir, f'{safe_id}.json')

    def get(self, draft_id: str) -> Optional[dict]:
        fpath = self._get_file(draft_id)
        if not os.path.exists(fpath):
            return None
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def save(self, draft_data: dict) -> dict:
        draft_id = draft_data.get('id') or str(uuid.uuid4())
        draft_data['id'] = draft_id
        draft_data['updatedAt'] = datetime.now().isoformat()
        if not draft_data.get('createdAt'):
            draft_data['createdAt'] = draft_data['updatedAt']
        fpath = self._get_file(draft_id)
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
        return draft_data

    def delete(self, draft_id: str) -> bool:
        """删除草稿（真正删除文件）"""
        fpath = self._get_file(draft_id)
        if os.path.exists(fpath):
            os.remove(fpath)
            return True
        return False
