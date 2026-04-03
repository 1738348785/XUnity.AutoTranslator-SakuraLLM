import re
import time
import requests

from .config import AppConfig
from .logging_bridge import LoggerBridge


APOLOGY_PHRASES = [
    "我很抱歉",
    "抱歉，我无法",
    "抱歉，您提供的内容",
    "请提供需要翻译的",
    "请告诉我您需要翻译的",
]

PROMPT_ECHO_PHRASES = [
    "视觉小说翻译模型",
    "通顺地将日文翻译成",
    "联系上下文正确使用人称代词",
    "不要混淆使役态和被动态",
    "不要擅自添加原文中没有的",
]

GARBAGE_PATTERNS = [
    "参考以下术语表",
    "根据以上术语表",
    "将下面的文本从日文翻译成",
    "请将以下日文翻译成",
    "翻译成简体中文",
    "历史翻译：",
    "src->dst",
]


class Translator:
    def __init__(self, config: AppConfig, logger: LoggerBridge):
        self.config = config
        self.logger = logger

    def strip_kaomoji_for_detection(self, text):
        if not text:
            return text

        def replace(match):
            segment = match.group(0)
            has_symbol_hint = re.search(r"[()（）'\"=^~`｀´◇▽≧ωー・<>♥♡❤★☆！？!?_/\\;:～~-]", segment)
            has_kanji = re.search(r"[\u4E00-\u9FFF]", segment)
            kana_chars = re.findall(r"[\u3040-\u309F\u30A0-\u30FF]", segment)
            ascii_words = re.findall(r"[A-Za-z0-9]{2,}", segment)
            if has_symbol_hint and not has_kanji and len(kana_chars) <= 3 and not ascii_words:
                return ""
            return segment

        return re.sub(r"[\(（][^()\r\n]{0,24}[\)）][ゞ゛゜ノﾉっッ]*", replace, text)

    def extract_japanese_fragments(self, text):
        cleaned = self.strip_kaomoji_for_detection(text)
        if not cleaned:
            return []

        raw_fragments = re.findall(r"[\u3040-\u3096\u309D-\u309F\u30A1-\u30FA\u30FC-\u30FE]{1,}", cleaned)
        fragments = []
        ignored_singletons = {"ー", "ノ", "ﾉ", "ゞ", "゛", "゜", "ッ", "っ"}

        for fragment in raw_fragments:
            fragment = fragment.strip()
            if not fragment:
                continue
            if fragment in ignored_singletons:
                continue
            if len(fragment) == 1 and fragment in ignored_singletons:
                continue
            fragments.append(fragment)
        return fragments

    def contains_japanese(self, text):
        return bool(self.extract_japanese_fragments(text))

    def has_meaningful_japanese_residue(self, text):
        fragments = self.extract_japanese_fragments(text)
        if not fragments:
            return False, []
        meaningful = []
        for fragment in fragments:
            if len(fragment) >= 2:
                meaningful.append(fragment)
                continue
            if fragment in {"あ", "い", "う", "え", "お", "ん", "ア", "イ", "ウ", "エ", "オ", "ン"}:
                meaningful.append(fragment)
        return bool(meaningful), meaningful

    def is_expressive_text(self, text):
        if not text:
            return False
        special_markers = ['♥', '♡', '❤', '★', '☆', 'っ♥', 'っ♪']
        if any(marker in text for marker in special_markers):
            return True
        dash_count = text.count('――') + text.count('——') + text.count('--')
        ellipsis_count = text.count('……') + text.count('...')
        if dash_count >= 2 or ellipsis_count >= 2 or (dash_count >= 1 and ellipsis_count >= 1):
            return True
        segments = re.split(r'[　\s]+', text.strip())
        if len(segments) >= 2:
            segment_counts = {}
            for seg in segments:
                if len(seg) > 1:
                    segment_counts[seg] = segment_counts.get(seg, 0) + 1
            if any(count > 1 for count in segment_counts.values()):
                return True
        return False

    def has_repeated_sequence(self, text, count):
        if not text or count <= 1:
            return False
        exclude_chars = set(
            "，。？！、…「」『』（）(),.!?~～♥♡❤★☆・―—-"
            "0123456789０１２３４５６７８９"
            "　 \t\n"
            "啊呀哦嗯呜哈唔噢嘿咦呵喂唤"
        )
        current_char = None
        run_length = 0
        for char in text:
            if char == current_char:
                run_length += 1
            else:
                current_char = char
                run_length = 1
            if char in exclude_chars:
                continue
            threshold = count + 3 if 0x4E00 <= ord(char) <= 0x9FFF else count
            if run_length >= threshold:
                return True
        exclude_patterns = {"……", "...", "~~", "♥♥", "！！", "??", "——", "――", "--"}
        max_size = min(len(text) // count, 8)
        for size in range(2, max_size + 1):
            for i in range(len(text) - size * count + 1):
                substring = text[i:i + size]
                if substring in exclude_patterns:
                    continue
                if all(c in exclude_chars for c in substring):
                    continue
                repeated = True
                for j in range(1, count):
                    start = i + j * size
                    if text[start:start + size] != substring:
                        repeated = False
                        break
                if repeated:
                    return True
        return False

    def process_special_chars(self, original_text, translated_text):
        if not translated_text:
            return translated_text
        if original_text.startswith("「") and original_text.endswith("」"):
            if not translated_text.startswith("「"):
                translated_text = "「" + translated_text
            if not translated_text.endswith("」"):
                translated_text = translated_text + "」"
        special_chars = ["……", "...", "，", "。", "？", "！"]
        orig_end = next((chars for chars in special_chars if original_text.endswith(chars)), "")
        trans_end = next((chars for chars in special_chars if translated_text.endswith(chars)), "")
        if orig_end:
            if trans_end and trans_end != orig_end:
                translated_text = translated_text[:-len(trans_end)] + orig_end
            elif not trans_end:
                translated_text += orig_end
        elif trans_end:
            translated_text = translated_text[:-len(trans_end)]
        return translated_text

    def resolve_newline_mode(self, show_warning=False):
        normalized = str(self.config.newline_mode).strip().lower()
        valid_modes = {"escape", "keep", "split_lines"}
        if normalized not in valid_modes:
            if show_warning:
                self.logger.warn(f"无效的 Newline_Mode: {self.config.newline_mode!r}，已回退到 escape")
            return "escape"
        return normalized

    def call_translation_api(self, text, model_params):
        headers = dict(self.config.custom_headers)
        reasoning_effort = headers.pop("reasoning_effort", None)
        request_data = {
            "model": self.config.model_type,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": text},
            ],
            "stream": False,
            **model_params,
        }
        if reasoning_effort is not None:
            request_data["reasoning_effort"] = reasoning_effort
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        response = requests.post(
            f"{self.config.base_url}/v1/chat/completions",
            json=request_data,
            headers=headers,
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        response_json = response.json()
        if "choices" in response_json:
            content = response_json["choices"][0]["message"]["content"]
        else:
            content = response_json.get("message", {}).get("content", "")
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        for pattern in GARBAGE_PATTERNS:
            if pattern in content:
                idx = content.find(pattern)
                if idx > 0:
                    content = content[:idx].strip()
                    break
        return content

    def is_mostly_kanji_or_simple(self, text):
        if not text:
            return False

        significant_chars = [char for char in text if not char.isspace()]
        if not significant_chars:
            return False

        kana_count = 0
        kanji_count = 0
        latin_count = 0
        digit_count = 0
        symbol_count = 0

        for char in significant_chars:
            code = ord(char)
            if 0x3040 <= code <= 0x309F:
                kana_count += 1
            elif 0x30A0 <= code <= 0x30FF:
                kana_count += 1
            elif 0x4E00 <= code <= 0x9FFF:
                kanji_count += 1
            elif char.isascii() and char.isalpha():
                latin_count += 1
            elif char.isdigit():
                digit_count += 1
            else:
                symbol_count += 1

        total = len(significant_chars)
        if latin_count > 0 and kanji_count == 0 and kana_count == 0:
            return False
        if kana_count == 0 and kanji_count > 0 and latin_count == 0:
            return True
        if kana_count == 0 and kanji_count > 0 and (digit_count + symbol_count) > 0 and latin_count == 0:
            return True
        if total > 0 and kana_count / total < 0.2 and kanji_count > 0 and latin_count == 0:
            return True
        return False

    def validate_translation(self, translation, original_text, original_japanese=None):
        if not translation or not translation.strip():
            return False, "empty", None
        if translation.strip() == original_text.strip():
            if self.is_mostly_kanji_or_simple(original_text):
                return True, "ok", None
            return False, "echo", None
        if any(phrase in translation for phrase in PROMPT_ECHO_PHRASES):
            return False, "prompt_echo", None
        if len(original_text) <= 10 and len(translation) > len(original_text) * 5:
            return False, "too_long", None
        if any(phrase in translation for phrase in APOLOGY_PHRASES):
            return False, "apology", None
        has_residue, fragments = self.has_meaningful_japanese_residue(translation)
        if has_residue:
            return False, "japanese", ", ".join(fragments[:3])
        check_text = original_japanese if original_japanese else original_text
        if not self.is_expressive_text(check_text):
            if self.has_repeated_sequence(translation, self.config.repeat_count):
                return False, "repeat", None
        return True, "ok", None

    def translate_text(self, text):
        original_text = text
        if text.startswith("「") and text.endswith("」"):
            text = text[1:-1]
        try:
            if self.is_mostly_kanji_or_simple(text) and len(text) <= 10:
                self.logger.info(f"[译文] {original_text} (短文本且主要为汉字/符号，跳过翻译)")
                return original_text
            model_params = {
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
            }
            translation = None
            is_valid = False
            retries = 0
            while retries < self.config.max_retries:
                try:
                    translation = self.call_translation_api(text, model_params)
                    is_valid, reason, detail = self.validate_translation(translation, text, original_text)
                    if is_valid:
                        break
                    if reason == "repeat":
                        self.logger.warn("检测到重复短语，调整参数重试")
                        self.logger.warn(f"[当前译文] {translation}")
                        model_params["frequency_penalty"] = min(model_params.get("frequency_penalty", 0) + 0.1, 1.0)
                        model_params["temperature"] = max(model_params["temperature"] - 0.05, 0.1)
                    elif reason == "japanese":
                        if detail:
                            self.logger.warn(f"译文包含日文残留片段: {detail}，重试中")
                        else:
                            self.logger.warn("译文包含日文，重试中")
                        self.logger.warn(f"[当前译文] {translation}")
                    elif reason == "apology":
                        self.logger.warn("模型拒绝翻译，调整参数重试")
                        self.logger.warn(f"[当前译文] {translation}")
                        model_params["temperature"] = min(model_params["temperature"] + 0.1, 0.5)
                    elif reason == "echo":
                        self.logger.warn("模型回显原文，重试")
                        model_params["temperature"] = min(model_params["temperature"] + 0.05, 0.5)
                    elif reason == "prompt_echo":
                        self.logger.warn("模型回显提示词，重试")
                        self.logger.warn(f"[当前译文] {translation}")
                    elif reason == "too_long":
                        self.logger.warn("译文过长，可能包含无关内容，重试中")
                        self.logger.warn(f"[当前译文] {translation}")
                        model_params["temperature"] = max(model_params["temperature"] - 0.05, 0.1)
                    elif reason == "empty":
                        self.logger.warn("翻译结果为空，重试中")
                    retries += 1
                except requests.exceptions.Timeout:
                    retries += 1
                    self.logger.error(f"API请求超时，第 {retries}/{self.config.max_retries} 次重试")
                    time.sleep(1)
                except requests.exceptions.RequestException as e:
                    retries += 1
                    self.logger.error(f"API请求失败: {e}，第 {retries}/{self.config.max_retries} 次重试")
                    time.sleep(1)
            if is_valid and translation:
                translation = self.process_special_chars(original_text, translation)
                self.logger.info(f"[译文] {translation}")
                return translation
            if translation:
                translation = self.process_special_chars(original_text, translation)
                self.logger.warn("翻译结果可能不完美，但仍输出")
                self.logger.warn(f"[译文] {translation}")
                return translation
            self.logger.error("翻译失败，无法获取翻译结果")
            return False
        except Exception as e:
            self.logger.error(f"翻译过程出错: {e}")
            return False

    def handle_translation(self, text):
        newline_mode = self.resolve_newline_mode()
        if newline_mode == "keep":
            return self.translate_text(text)
        if newline_mode == "split_lines":
            parts = re.split(r'(\r\n|\r|\n)', text)
            translated_parts = []
            for part in parts:
                if part in {"\r\n", "\r", "\n"}:
                    translated_parts.append(part)
                elif part:
                    translated = self.translate_text(part)
                    if translated is False:
                        return False
                    translated_parts.append(translated)
                else:
                    translated_parts.append(part)
            return "".join(translated_parts)
        escaped_text = text.replace("\n", "\\n")
        translation = self.translate_text(escaped_text)
        if isinstance(translation, str):
            return translation.replace("\\n", "\n")
        return translation
