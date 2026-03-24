from flask import Flask, request, render_template_string
from gevent.pywsgi import WSGIServer
import os
import re
import time
import requests

# 启用虚拟终端序列，支持ANSI转义代码
os.system("")

# ==================== 配置区域 ====================
# API配置
Base_url = "http://127.0.0.1:8080"  # API 请求地址
API_Key = ""  # API 密钥，需要鉴权时填写，留空则不发送 Authorization 请求头
Custom_Headers = {
    # "reasoning_effort": "low",
    # "X-Your-Header": "your-value",
}
Model_Type = "GalTransl-v4-4B-2601"  # 模型名称，本地部署好像随意，填或不填好像都行
Request_Timeout = 20 # 请求超时时间（秒）
Newline_Mode = "escape"  # 换行处理模式：escape(转义后整体翻译) / keep(保留换行整体翻译) / split_lines(按行分别翻译)

# 翻译质量控制
repeat_count = 8  # 译文中有任意单字或单词连续出现大于等于此次数，则重试
max_retries = 3  # 最大重试次数

# 模型参数
default_model_params = {
    "temperature": 0.3,  # v3推荐值
    "max_tokens": 2048,
    "top_p": 0.8,  # v3推荐值
    "frequency_penalty": 0.0,
}

# ==================== 提示词配置 ====================
system_prompt = """你是一个视觉小说翻译模型，可以通顺地使用给定的术语表以指定的风格将日文翻译成简体中文，并联系上下文正确使用人称代词，注意不要混淆使役态和被动态的主语和宾语，不要擅自添加原文中没有的特殊符号，也不要擅自增加或减少换行。"""

# 模型拒绝翻译时的常见回复
apology_phrases = [
    "我很抱歉",
    "抱歉，我无法",
    "抱歉，您提供的内容",
    "请提供需要翻译的",
    "请告诉我您需要翻译的",
]

# 检测系统提示词或翻译指令回显的关键短语
prompt_echo_phrases = [
    "视觉小说翻译模型",
    "流畅地将日文翻译成",
    "联系上下文正确使用人称代词",
    "不要混淆使役态和被动态",
    "不要擅自添加原文中没有的",
]

# 用于清理模型输出中的垃圾内容（训练数据残留、提示词模板等）
garbage_patterns = [
    "参考以下术语表",
    "根据以上术语表",
    "将下面的文本从日文翻译成",
    "请将以下日文翻译成",
    "翻译成简体中文",
    "历史翻译：",
    "src->dst",
]

# ==================== 初始化 ====================
app = Flask(__name__)


# ==================== 工具函数 ====================
def contains_japanese(text):
    """检测文本是否包含日文字符（平假名、片假名）"""
    pattern = re.compile(r"[\u3040-\u3096\u309D-\u309F\u30A1-\u30FA\u30FC-\u30FE]")
    return pattern.search(text) is not None


def is_expressive_text(text):
    """检测文本是否为拟声词/情感表达/重复语气（本身就包含有意的重复模式）
    
    这类文本的翻译自然会有重复，应该跳过重复检测
    例如：「ふぅ゛ー……っ♥　ふぅ゛ー……っ♥」
    或者：（戻りたくない――戻りたく――）
    """
    if not text:
        return False
    
    # 检测特征：
    # 1. 包含特殊符号（心形、星形等）
    # 2. 包含多个省略号或破折号（表示语气重复或拖长）
    # 3. 包含拟声词常见的假名模式
    
    special_markers = ['♥', '♡', '❤', '★', '☆', 'っ♥', 'っ♪']
    
    # 如果包含心形等特殊符号，很可能是情感表达
    if any(marker in text for marker in special_markers):
        return True
    
    # 检测是否包含多个破折号或省略号（表示语气重复或拖长）
    # 如果出现2次以上，可能是有意的重复
    dash_count = text.count('――') + text.count('——') + text.count('--')
    ellipsis_count = text.count('……') + text.count('...')
    if dash_count >= 2 or ellipsis_count >= 2 or (dash_count >= 1 and ellipsis_count >= 1):
        return True
    
    # 检测是否有类似的重复模式（同样的拟声词出现多次）
    # 检查是否有空格分隔的重复片段
    segments = re.split(r'[　\s]+', text.strip())
    if len(segments) >= 2:
        # 检查是否有重复的片段
        segment_counts = {}
        for seg in segments:
            if len(seg) > 1:  # 忽略单字符
                segment_counts[seg] = segment_counts.get(seg, 0) + 1
        # 如果有任何片段出现超过1次，就是有意的重复
        if any(count > 1 for count in segment_counts.values()):
            return True
    
    return False


def has_repeated_sequence(text, count):
    """检测是否有过度重复的单字或短语（连续出现）

    注意：这个检测应该比较宽松，只有真正异常的连续重复才返回 True
    某些字符在原文中本来就会重复出现（如感叹词、符号等），应排除这些字符
    """
    if not text or count <= 1:
        return False

    # 排除的字符：标点、符号、数字、以及常见的可重复字符
    exclude_chars = set(
        "，。？！、…「」『』（）(),.!?~～♥♡❤★☆・―—-" +  # 标点和符号
        "0123456789０１２３４５６７８９" +  # 数字
        "　 \t\n" +  # 空白字符
        "啊呀哦嗯呜哈唔噢嘿咦呵喂唤"  # 常见感叹词
    )

    # 检查单个字符的连续重复 - 只检测真正异常的重复
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

        # 中文字符需要更高的量才认为是问题
        threshold = count + 3 if 0x4E00 <= ord(char) <= 0x9FFF else count
        if run_length >= threshold:
            return True

    # 检查短语的连续重复
    exclude_patterns = {"……", "...", "~~", "♥♥", "！！", "??", "——", "――", "--"}
    max_size = min(len(text) // count, 8)

    for size in range(2, max_size + 1):
        for i in range(len(text) - size * count + 1):
            substring = text[i:i + size]

            # 跳过被排除的模式
            if substring in exclude_patterns:
                continue

            # 跳过全是排除字符的子串
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


def process_special_chars(original_text, translated_text):
    """处理特殊字符（引号和标点）"""
    if not translated_text:
        return translated_text

    # 处理「」引号
    if original_text.startswith("「") and original_text.endswith("」"):
        if not translated_text.startswith("「"):
            translated_text = "「" + translated_text
        if not translated_text.endswith("」"):
            translated_text = translated_text + "」"

    # 处理末尾标点同步
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


def resolve_newline_mode(show_warning=False):
    """规范化换行处理模式，非法值回退到 escape"""
    normalized = str(Newline_Mode).strip().lower()
    valid_modes = {"escape", "keep", "split_lines"}

    if normalized not in valid_modes:
        if show_warning:
            print(f"\033[33m[WARN] 无效的 Newline_Mode: {Newline_Mode!r}，已回退到 escape\033[0m")
        return "escape"

    return normalized


def call_translation_api(text, model_params):
    """调用翻译API"""
    user_content = text

    headers = dict(Custom_Headers)
    reasoning_effort = headers.pop("reasoning_effort", None)

    request_data = {
        "model": Model_Type,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        **model_params,
    }
    if reasoning_effort is not None:
        request_data["reasoning_effort"] = reasoning_effort

    if API_Key:
        headers["Authorization"] = f"Bearer {API_Key}"

    response = requests.post(
        f"{Base_url}/v1/chat/completions",
        json=request_data,
        headers=headers,
        timeout=Request_Timeout
    )
    response.raise_for_status()
    
    response_json = response.json()
    if "choices" in response_json:
        content = response_json["choices"][0]["message"]["content"]
    else:
        content = response_json.get("message", {}).get("content", "")
    
    # 移除 <think> 标签及其内容（如果有）
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    
    # 清理模型输出中的垃圾内容（训练数据残留）
    # 找到第一个垃圾模式出现的位置，截断其之前的内容
    for pattern in garbage_patterns:
        if pattern in content:
            idx = content.find(pattern)
            if idx > 0:  # 确保不是在开头
                content = content[:idx].strip()
                break
    
    return content


def is_mostly_kanji_or_simple(text):
    """检测文本是否主要由汉字、数字、符号组成（不需要翻译或翻译后相同）
    
    这类文本包括：
    - 纯汉字文本（如：新規、学校、教室）
    - 汉字+数字/符号（如：堕落度: 1、HP: 100）
    - 单词或短语（如：OK、START）
    """
    if not text:
        return False
    
    # 统计各类字符
    kanji_count = 0  # 汉字（中日共用）
    hiragana_count = 0  # 平假名
    katakana_count = 0  # 片假名
    other_count = 0  # 数字、符号、空格等
    
    for char in text:
        code = ord(char)
        if 0x4E00 <= code <= 0x9FFF:  # CJK统一汉字
            kanji_count += 1
        elif 0x3040 <= code <= 0x309F:  # 平假名
            hiragana_count += 1
        elif 0x30A0 <= code <= 0x30FF:  # 片假名
            katakana_count += 1
        else:
            other_count += 1  # 数字、符号、空格、英文等
    
    total = len(text)
    japanese_only = hiragana_count + katakana_count
    
    # 如果没有平假名/片假名，或者平假名/片假名只占很小比例，则认为不需要翻译
    # 这类文本主要是汉字+数字/符号，翻译后可能和原文相同
    if japanese_only == 0:
        return True
    
    # 如果日文假名占比很低（小于20%），也可能翻译后相同
    if total > 0 and japanese_only / total < 0.2:
        return True
    
    return False


def validate_translation(translation, original_text, original_japanese=None):
    """验证翻译结果质量
    
    Args:
        translation: 翻译结果
        original_text: 用于对比的文本（可能已移除引号）
        original_japanese: 原始日文文本（用于检测是否为拟声词）
    """
    # 检查是否为空
    if not translation or not translation.strip():
        return False, "empty"
    
    # 检查翻译结果是否就是原文
    if translation.strip() == original_text.strip():
        # 如果原文主要是汉字/数字/符号，译文和原文相同是正常的
        if is_mostly_kanji_or_simple(original_text):
            return True, "ok"
        # 否则才认为是回显问题
        return False, "echo"
    
    # 检查是否回显了系统提示词或翻译指令
    if any(phrase in translation for phrase in prompt_echo_phrases):
        return False, "prompt_echo"
    
    # 检查译文是否过长（相对于原文），可能包含了无关内容
    # 短文本的译文不应该超过原文长度的5倍
    if len(original_text) <= 10 and len(translation) > len(original_text) * 5:
        return False, "too_long"
    
    # 检查是否为拒绝回复
    if any(phrase in translation for phrase in apology_phrases):
        return False, "apology"
    
    # 检查是否包含日文
    if contains_japanese(translation):
        return False, "japanese"
    
    # 检查是否有过多重复
    # 但如果原文本身就是拟声词/情感表达（有意的重复），则跳过此检测
    check_text = original_japanese if original_japanese else original_text
    if not is_expressive_text(check_text):
        if has_repeated_sequence(translation, repeat_count):
            return False, "repeat"
    
    return True, "ok"


# ==================== 翻译核心逻辑 ====================
def translate_text(text):
    """翻译单段文本（不负责换行模式分发）"""

    original_text = text  # 保存原始文本用于特殊字符处理

    # 如果文本被「」包裹，在翻译时先移除
    if text.startswith("「") and text.endswith("」"):
        text = text[1:-1]

    try:
        # 检查是否为极短的纯汉字/中性文本，直接返回原文
        # 这类文本翻译后应该相同，且容易导致模型回显提示词
        if is_mostly_kanji_or_simple(text) and len(text) <= 10:
            print(f"\033[36m[译文]\033[0m: \033[32m{original_text}\033[0m (纯汉字/符号，跳过翻译)")
            print("-" * 80)
            return original_text

        # 复制模型参数
        model_params = default_model_params.copy()

        translation = None
        is_valid = False
        retries = 0

        while retries < max_retries:
            try:
                # 调用API
                translation = call_translation_api(text, model_params)

                # 验证翻译质量
                is_valid, reason = validate_translation(translation, text, original_text)

                if is_valid:
                    break
                elif reason == "repeat":
                    print(f"\033[33m[WARN] 检测到重复短语，调整参数重试\033[0m")
                    print(f"\033[33m[当前译文]: {translation}\033[0m")
                    model_params["frequency_penalty"] = min(model_params.get("frequency_penalty", 0) + 0.1, 1.0)
                    model_params["temperature"] = max(model_params["temperature"] - 0.05, 0.1)
                    retries += 1
                elif reason == "japanese":
                    print(f"\033[33m[WARN] 译文包含日文，重试中\033[0m")
                    print(f"\033[33m[当前译文]: {translation}\033[0m")
                    retries += 1
                elif reason == "apology":
                    print(f"\033[33m[WARN] 模型拒绝翻译，调整参数重试\033[0m")
                    print(f"\033[33m[当前译文]: {translation}\033[0m")
                    model_params["temperature"] = min(model_params["temperature"] + 0.1, 0.5)
                    retries += 1
                elif reason == "echo":
                    print(f"\033[33m[WARN] 模型回显原文，重试\033[0m")
                    model_params["temperature"] = min(model_params["temperature"] + 0.05, 0.5)
                    retries += 1
                elif reason == "prompt_echo":
                    print(f"\033[33m[WARN] 模型回显提示词，重试\033[0m")
                    print(f"\033[33m[当前译文]: {translation}\033[0m")
                    retries += 1
                elif reason == "too_long":
                    print(f"\033[33m[WARN] 译文过长，可能包含无关内容，重试中\033[0m")
                    print(f"\033[33m[当前译文]: {translation}\033[0m")
                    model_params["temperature"] = max(model_params["temperature"] - 0.05, 0.1)
                    retries += 1
                elif reason == "empty":
                    print(f"\033[33m[WARN] 翻译结果为空，重试中\033[0m")
                    retries += 1

            except requests.exceptions.Timeout:
                retries += 1
                print(f"\033[31m[ERROR] API请求超时，第 {retries}/{max_retries} 次重试\033[0m")
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                retries += 1
                print(f"\033[31m[ERROR] API请求失败: {e}，第 {retries}/{max_retries} 次重试\033[0m")
                time.sleep(1)

        if is_valid and translation:
            # 处理特殊字符
            translation = process_special_chars(original_text, translation)

            print(f"\033[36m[译文]\033[0m: \033[32m{translation}\033[0m")
            print("-" * 80)
            return translation
        elif translation:
            # 即使验证失败，也输出翻译结果（比完全失败好）
            translation = process_special_chars(original_text, translation)

            print(f"\033[33m[WARN] 翻译结果可能不完美，但仍输出\033[0m")
            print(f"\033[36m[译文]\033[0m: \033[33m{translation}\033[0m")
            print("-" * 80)
            return translation
        else:
            print(f"\033[31m[ERROR] 翻译失败，无法获取翻译结果\033[0m")
            return False

    except Exception as e:
        print(f"\033[31m[ERROR] 翻译过程出错: {e}\033[0m")
        return False


def handle_translation(text):
    """根据换行模式处理翻译请求"""
    newline_mode = resolve_newline_mode()

    if newline_mode == "keep":
        return translate_text(text)

    if newline_mode == "split_lines":
        parts = re.split(r'(\r\n|\r|\n)', text)
        translated_parts = []

        for part in parts:
            if part in {"\r\n", "\r", "\n"}:
                translated_parts.append(part)
            elif part:
                translated = translate_text(part)
                if translated is False:
                    return False
                translated_parts.append(translated)
            else:
                translated_parts.append(part)

        return "".join(translated_parts)

    escaped_text = text.replace("\n", "\\n")
    translation = translate_text(escaped_text)
    if isinstance(translation, str):
        return translation.replace("\\n", "\n")
    return translation

# ==================== Flask 路由 ====================
@app.route("/translate", methods=["GET"])
def translate():
    """翻译API端点"""
    text = request.args.get("text")
    if not text:
        return "缺少text参数", 400

    print(f"\033[36m[原文]\033[0m: \033[35m{text}\033[0m")

    translation = handle_translation(text)

    if isinstance(translation, str):
        return translation
    else:
        return "[翻译失败] " + text, 500


@app.route("/", methods=["GET"])
def index():
    """首页"""
    return render_template_string("""
        <h1>SakuraLLM 翻译服务已启动</h1>
        <p>请访问 <code>/translate?text=你的文本</code> 进行翻译</p>
        <p>当前模型: <strong>{{ model }}</strong></p>
    """, model=Model_Type)


# ==================== 启动服务 ====================
def main():
    newline_mode = resolve_newline_mode(show_warning=True)

    print("\033[32m" + "=" * 60 + "\033[0m")
    print(f"\033[32m  SakuraLLM 翻译服务启动中...\033[0m")
    print(f"\033[32m  地址: http://127.0.0.1:4000\033[0m")
    print(f"\033[32m  模型: {Model_Type}\033[0m")
    print(f"\033[32m  换行模式: {newline_mode}\033[0m")
    print(f"\033[32m  参数: temperature={default_model_params['temperature']}, top_p={default_model_params['top_p']}\033[0m")
    print("\033[32m" + "=" * 60 + "\033[0m")

    http_server = WSGIServer(("127.0.0.1", 4000), app, log=None, error_log=None)

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[31m服务器已停止\033[0m")


if __name__ == "__main__":
    main()
