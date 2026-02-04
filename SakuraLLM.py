from flask import Flask, request, render_template_string
from gevent.pywsgi import WSGIServer
from urllib.parse import unquote
from queue import Queue
import concurrent.futures
import os
import re
import time
import requests

# 启用虚拟终端序列，支持ANSI转义代码
os.system("")

# ==================== 配置区域 ====================
# API配置
Base_url = "http://127.0.0.1:8080"  # API 请求地址
Model_Type = "GalTransl-v4-4B-2601"  # 模型名称，本地部署好像随意，填或不填好像都行
Request_Timeout = 20 # 请求超时时间（秒）

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
    """检测是否有过度重复的短语或单字
    
    注意：这个检测应该比较宽松，只有真正异常的重复才返回true
    某些字符在原文中本来就会重复出现（如感叹词、符号等），应排除这些字符
    """
    if not text or len(text) < count:
        return False
    
    # 排除的字符：标点、符号、数字、以及常见的可重复字符
    exclude_chars = set(
        "，。？！、…「」『』（）(),.!?~～♥♡❤★☆・―—-" +  # 标点和符号
        "0123456789０１２３４５６７８９" +  # 数字
        "　 \t\n" +  # 空白字符
        "啊呀哦嗯呜哈唔噢嘿咦呵喂唤"  # 常见感叹词
    )
    
    # 检查单个字符的重复 - 只检测真正异常的重复
    for char in set(text):
        if char not in exclude_chars:
            char_count = text.count(char)
            # 中文字符需要更高的量才认为是问题
            if ord(char) > 0x4E00:  # 中文范围
                if char_count >= count + 3:
                    return True
            else:
                if char_count >= count:
                    return True

    # 检查短语重复（3字符及以上）- 只检测较长的重复短语
    # 排除常见的重复模式
    exclude_patterns = {"……", "...", "~~", "♥♥", "！！", "??", "——", "――", "--"}
    
    # 只检查3字符及以上的重复
    max_size = min(len(text) // count + 1, 8)
    for size in range(3, max_size):
        seen = {}
        for i in range(len(text) - size + 1):
            substring = text[i:i + size]
            # 跳过被排除的模式
            if substring in exclude_patterns:
                continue
            # 跳过全是排除字符的子串
            if all(c in exclude_chars for c in substring):
                continue
            seen[substring] = seen.get(substring, 0) + 1
            # 需要更高的重复次数才触发
            if seen[substring] >= count:
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
    special_chars = ["，", "。", "？", "！", "..."]
    orig_end = original_text[-1] if original_text else ""
    trans_end = translated_text[-1] if translated_text else ""
    
    if orig_end in special_chars:
        if trans_end in special_chars and trans_end != orig_end:
            translated_text = translated_text[:-1] + orig_end
        elif trans_end not in special_chars:
            translated_text += orig_end
    elif trans_end in special_chars:
        translated_text = translated_text[:-1]
    
    return translated_text





def call_translation_api(text, model_params):
    """调用翻译API"""
    user_content = text
    
    request_data = {
        "model": Model_Type,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        **model_params,
    }
    
    response = requests.post(
        f"{Base_url}/v1/chat/completions",
        json=request_data,
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
def handle_translation(text, translation_queue):
    """处理翻译请求的核心函数"""
    
    text = unquote(text)
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
            translation_queue.put(original_text)
            return
        
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
            translation_queue.put(translation)
        elif translation:
            # 即使验证失败，也输出翻译结果（比完全失败好）
            translation = process_special_chars(original_text, translation)
            
            print(f"\033[33m[WARN] 翻译结果可能不完美，但仍输出\033[0m")
            print(f"\033[36m[译文]\033[0m: \033[33m{translation}\033[0m")
            print("-" * 80)
            translation_queue.put(translation)
        else:
            print(f"\033[31m[ERROR] 翻译失败，无法获取翻译结果\033[0m")
            translation_queue.put(False)
            
    except Exception as e:
        print(f"\033[31m[ERROR] 翻译过程出错: {e}\033[0m")
        translation_queue.put(False)


# ==================== Flask 路由 ====================
@app.route("/translate", methods=["GET"])
def translate():
    """翻译API端点"""
    text = request.args.get("text")
    if not text:
        return "缺少text参数", 400
    
    print(f"\033[36m[原文]\033[0m: \033[35m{text}\033[0m")
    
    # 处理换行符
    text = text.replace("\n", "\\n")
    
    translation_queue = Queue()
    
    # 使用线程池处理翻译
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(handle_translation, text, translation_queue)
        
        try:
            future.result(timeout=Request_Timeout + 5)
        except concurrent.futures.TimeoutError:
            print("\033[31m[ERROR] 翻译请求超时\033[0m")
            return "[请求超时] " + text, 500
    
    translation = translation_queue.get()
    
    if isinstance(translation, str):
        translation = translation.replace("\\n", "\n")
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
    print("\033[32m" + "=" * 60 + "\033[0m")
    print(f"\033[32m  SakuraLLM 翻译服务启动中...\033[0m")
    print(f"\033[32m  地址: http://127.0.0.1:4000\033[0m")
    print(f"\033[32m  模型: {Model_Type}\033[0m")
    print(f"\033[32m  参数: temperature={default_model_params['temperature']}, top_p={default_model_params['top_p']}\033[0m")
    print("\033[32m" + "=" * 60 + "\033[0m")
    
    http_server = WSGIServer(("127.0.0.1", 4000), app, log=None, error_log=None)
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[31m服务器已停止\033[0m")


if __name__ == "__main__":
    main()
