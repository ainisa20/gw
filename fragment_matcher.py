#!/usr/bin/env python3
import json
import os
import re
from urllib.request import Request as UrllibRequest, urlopen
from urllib.error import URLError
from typing import Optional, Dict, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAGMENTS_FILE = os.path.join(SCRIPT_DIR, "fragments_structured.json")


class FragmentMatcher:
    def __init__(self, fragments_file: str = FRAGMENTS_FILE):
        with open(fragments_file, 'r', encoding='utf-8') as f:
            self.fragments = json.load(f)
        self.title_index = {}
        for frag in self.fragments:
            self.title_index[frag['title']] = frag

    def build_catalog_text(self) -> str:
        """构建分类目录文本，供模型分类使用"""
        from collections import OrderedDict
        sections = OrderedDict()
        for frag in self.fragments:
            sec = frag.get('section') or self._infer_section(frag)
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(frag)

        lines = []
        for sec, frags in sections.items():
            lines.append(f"【{sec}】")
            for frag in frags:
                lines.append(f"  {frag['id']}. {frag['title']} ({frag.get('step_label', '')})")
            lines.append("")

        return '\n'.join(lines)

    def _infer_section(self, frag: dict) -> str:
        label = frag.get('step_label', '')
        if '办理入口' in label:
            return '办理入口'
        if '实名认证确认' in label:
            return '实名认证确认'
        if '实名认证' in label:
            return '实名认证'
        if '名称自主申报' in label:
            return '名称自主申报'
        if '填写申请信息' in label:
            return '填写申请信息'
        if '流程办理方式' in label:
            return '流程办理方式'
        if '非全流程办理' in label:
            return '非全流程办理'
        if '业务审核' in label:
            return '业务审核'
        if '领取营业执照' in label:
            return '领取营业执照'
        if '领取印章' in label:
            return '领取印章'
        if '服务大厅' in frag.get('title', ''):
            return '服务大厅地址'
        if '电子印章' in frag.get('title', '') or '签章' in frag.get('title', ''):
            return '电子印章'
        if '全流程' in frag.get('title', ''):
            return '流程办理方式'
        return '其他步骤'

    def find_by_title(self, title: str) -> Optional[Dict]:
        """精确 title 匹配"""
        if title in self.title_index:
            return self.title_index[title]

        for frag in self.fragments:
            if title in frag['title'] or frag['title'] in title:
                return frag

        return None

    def find_by_id(self, fragment_id: int) -> Optional[Dict]:
        for frag in self.fragments:
            if frag.get('id') == fragment_id:
                return frag
        return None

    def match_hybrid(self, ocr_keywords: List[str]) -> Tuple[Optional[Dict], str, float]:
        """fallback：基于关键词的匹配"""
        if not ocr_keywords:
            return None, "无关键词", 0.0

        ocr_set = set(ocr_keywords)
        scores = []

        for frag in self.fragments:
            frag_keywords = frag.get('keywords', [])
            score = 0.0
            exact_matches = ocr_set & set(frag_keywords)
            score += len(exact_matches) * 10
            for kw in exact_matches:
                score += (10 - min(self._keyword_freq(kw), 10))
            for ocr_kw in ocr_keywords:
                for frag_kw in frag_keywords:
                    if ocr_kw in frag_kw or frag_kw in ocr_kw:
                        score += 3
                        break
            if score > 0:
                scores.append((frag, score))

        if not scores:
            return None, "未找到匹配片段", 0.0

        scores.sort(key=lambda x: x[1], reverse=True)
        best_frag, best_score = scores[0]
        return best_frag, f"关键词匹配 (分数{best_score:.0f})", best_score

    def _keyword_freq(self, kw: str) -> int:
        if not hasattr(self, '_freq_cache'):
            from collections import Counter
            all_kws = []
            for f in self.fragments:
                all_kws.extend(f.get('keywords', []))
            self._freq_cache = dict(Counter(all_kws))
        return self._freq_cache.get(kw, 0)

    def format_fragment_for_ai(self, fragment: Dict) -> str:
        lines = [
            f"## {fragment.get('title', '未知步骤')}",
            f"**步骤**: {fragment.get('step_label', '')}",
        ]
        if fragment.get('tips'):
            lines.append(f"**注意事项**: {fragment['tips']}")
        lines.append(f"\n**操作说明**:\n{fragment.get('context_text', '')}")
        return '\n'.join(lines)


class ScreenshotClassifier:
    """用模型对截图进行分类，直接返回匹配的 title"""

    def __init__(self, dify_base_url: str, dify_token: str, fragments_file: str = FRAGMENTS_FILE):
        self.dify_base_url = dify_base_url
        self.dify_token = dify_token
        self.matcher = FragmentMatcher(fragments_file)
        self._catalog = None

    def _get_catalog(self) -> str:
        if self._catalog is None:
            self._catalog = self.matcher.build_catalog_text()
        return self._catalog

    def classify(self, image_file_id: str, user_id: str = "default") -> Optional[Dict]:
        catalog = self._get_catalog()

        prompt = f"""请分析这张截图，判断它属于以下哪个操作步骤。

以下是所有可能的步骤分类目录：
{catalog}

请根据截图中的界面元素（标题、按钮、字段、选项等），判断当前截图最匹配哪个步骤。

返回JSON格式（只返回JSON，不要其他文字）：
{{{{
  "matched_title": "完整复制上面目录中的title",
  "matched_id": 对应的数字ID,
  "section": "所属分类",
  "step_label": "步骤标签",
  "confidence": 0.95,
  "reason": "简要说明判断依据"
}}}}

如果无法判断，返回：
{{{{
  "matched_title": null,
  "matched_id": null,
  "confidence": 0,
  "reason": "无法识别"
}}}}"""

        try:
            body = json.dumps({
                "query": prompt,
                "response_mode": "blocking",
                "user": user_id,
                "inputs": {},
                "files": [
                    {
                        "type": "image",
                        "transfer_method": "local_file",
                        "upload_file_id": image_file_id
                    }
                ]
            }).encode('utf-8')

            url = self.dify_base_url + "/v1/chat-messages"
            req = UrllibRequest(url, data=body, method="POST")
            req.add_header("Authorization", "Bearer " + self.dify_token)
            req.add_header("Content-Type", "application/json")

            resp = urlopen(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            answer = result.get('answer', '')

            print(f"[classify] 模型返回: {answer[:300]}")

            parsed = self._parse_response(answer)
            if not parsed or not parsed.get('matched_id'):
                return None

            # 用 ID 精确查找
            fragment = self.matcher.find_by_id(parsed['matched_id'])
            if fragment:
                return {
                    "fragment": fragment,
                    "confidence": parsed.get('confidence', 0),
                    "reason": parsed.get('reason', ''),
                    "method": "模型直接分类"
                }

            # ID 没找到，用 title 模糊匹配
            if parsed.get('matched_title'):
                fragment = self.matcher.find_by_title(parsed['matched_title'])
                if fragment:
                    return {
                        "fragment": fragment,
                        "confidence": parsed.get('confidence', 0),
                        "reason": parsed.get('reason', ''),
                        "method": "模型分类(title模糊匹配)"
                    }

            return None

        except URLError as e:
            print(f"[classify] API请求失败: {e}")
            return None
        except Exception as e:
            print(f"[classify] 分类失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_response(self, response: str) -> Optional[Dict]:
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if 'matched_id' in data or 'matched_title' in data:
                    return data
            except json.JSONDecodeError:
                pass

        # 尝试更大的JSON块
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None


_matcher_instance = None
_classifier_instance = None


def get_matcher() -> FragmentMatcher:
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = FragmentMatcher()
    return _matcher_instance


def get_classifier(dify_base_url: str = None, dify_token: str = None) -> ScreenshotClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        if dify_base_url is None or dify_token is None:
            raise ValueError("首次初始化需要传入 dify_base_url 和 dify_token")
        _classifier_instance = ScreenshotClassifier(dify_base_url, dify_token)
    return _classifier_instance
