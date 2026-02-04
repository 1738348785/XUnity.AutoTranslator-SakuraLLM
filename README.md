# SakuraLLM 翻译服务

[English Version](README_en.md)

## 简介

这是一个基于 Flask 的游戏翻译桥接服务，用于将 XUnity.AutoTranslator 与 SakuraLLM（或兼容 OpenAI API 的翻译模型）连接起来，将游戏中的日语文本翻译成简体中文。

该服务专为视觉小说/Galgame 翻译优化，支持智能翻译质量控制和自动重试机制。

## 功能特性

### 翻译质量控制
- **智能验证**：自动检测翻译结果质量，识别空翻译、回显原文、包含日文等问题
- **重复检测**：检测译文中的异常重复短语，自动调整参数重试
- **拟声词识别**：智能识别拟声词/情感表达文本，避免误判有意的重复模式
- **垃圾内容清理**：自动清理模型输出中的训练数据残留

### 自动重试机制
- **动态参数调整**：根据翻译失败原因自动调整 temperature、frequency_penalty 等参数
- **超时重试**：API 请求超时自动重试
- **最大重试次数**：可配置的重试次数上限

### 文本处理
- **特殊字符处理**：自动处理「」引号，保持格式一致
- **标点同步**：自动同步原文与译文的末尾标点
- **Think 标签清理**：自动移除模型输出中的 `<think>` 标签内容

## 环境要求

- Python 3.7+
- 运行中的 SakuraLLM 或兼容 OpenAI API 的翻译服务

## 安装

### 1. 安装依赖

```bash
pip install flask gevent requests
```

### 2. 配置服务

编辑 `SakuraLLM.py` 中的配置区域：

```python
# API配置
Base_url = "http://127.0.0.1:8080"  # API 请求地址
Model_Type = "GalTransl-v4-4B-2601"  # 模型名称
Request_Timeout = 20  # 请求超时时间（秒）

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
```

### 3. 启动服务

```bash
python SakuraLLM.py
```

服务启动后，将在 `http://127.0.0.1:4000` 监听请求。

## 使用方法

### API 端点

- **首页**：`GET /` - 显示服务状态
- **翻译**：`GET /translate?text=你的文本` - 翻译指定文本

### 配置 XUnity.AutoTranslator

在 `AutoTranslatorConfig.ini` 中添加以下配置：

```ini
[Service]
Endpoint=CustomTranslate
FallbackEndpoint=

[Custom]
Url=http://127.0.0.1:4000/translate
```

## 配置说明

### 模型参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `temperature` | 控制输出随机性，值越低越稳定 | 0.3 |
| `max_tokens` | 最大输出 token 数 | 2048 |
| `top_p` | 核采样参数 | 0.8 |
| `frequency_penalty` | 频率惩罚，用于减少重复 | 0.0 |

### 翻译质量配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `repeat_count` | 触发重复检测的阈值 | 8 |
| `max_retries` | 最大重试次数 | 3 |
| `Request_Timeout` | API 请求超时时间（秒） | 30 |

## 日志输出

服务运行时会输出彩色日志：

- 🔵 **[原文]**：收到的原始日文文本
- 🟢 **[译文]**：成功翻译的结果
- 🟡 **[WARN]**：翻译质量警告（重复、包含日文等）
- 🔴 **[ERROR]**：翻译失败或 API 错误

## 注意事项

1. 确保 SakuraLLM 或兼容的翻译 API 服务已启动
2. 检查 `Base_url` 配置是否正确指向你的模型服务地址
3. 如遇到翻译质量问题，可尝试调整 `temperature` 和 `top_p` 参数
4. 建议使用 SakuraLLM v3 或更新版本的模型
5. 经测试，笔记本 RTX 4070 在 GalTransl-v4-4B-2601 模型上速度很快，可实现实时翻译（RTX 4060/4060 Ti 同级别显卡预计也有类似表现）

## 致谢

- 感谢 [SakuraLLM](https://github.com/SakuraLLM/Sakura-13B-Galgame) 项目提供的翻译模型
- 感谢 [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator) 提供的游戏翻译框架
- 感谢 [as176590811/XUnity.AutoTranslator-chatgpt](https://github.com/as176590811/XUnity.AutoTranslator-chatgpt) 的原始代码支持
- 感谢 [SKIPPINGpetticoatconvent/XUnity.AutoTranslator-ollama](https://github.com/SKIPPINGpetticoatconvent/XUnity.AutoTranslator-ollama) 的代码修改
- 感谢 [PiDanShouRouZhouXD/Sakura_Launcher_GUI](https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI) 提供的 Sakura 启动器

## 许可证

MIT License
