# SakuraLLM Translation Service

[中文版本](README.md)

## Introduction

A Flask-based game translation bridge service that connects XUnity.AutoTranslator with SakuraLLM (or OpenAI API-compatible translation models) to translate Japanese text in games into Simplified Chinese.

This service is optimized for visual novel/Galgame translation, featuring intelligent translation quality control and automatic retry mechanisms.

## GUI Version (Recommended)

A version with a graphical user interface is now available for users who prefer not to use the command line:

- **GUI Branch**: [gui-main](https://github.com/1738348785/XUnity.AutoTranslator-SakuraLLM/tree/gui-main)
- **Latest Release**: [GUI v1.0.0 Releases](https://github.com/1738348785/XUnity.AutoTranslator-SakuraLLM/releases/tag/gui-v1.0.0)

## Features

### Translation Quality Control
- **Smart Validation**: Automatically detects translation quality issues such as empty translations, echoing original text, or containing Japanese characters
- **Repetition Detection**: Detects abnormal consecutive repeated phrases or characters in translations and automatically adjusts parameters for retry
- **Onomatopoeia Recognition**: Intelligently identifies onomatopoeia/emotional expressions to avoid false positives on intentional repetition patterns
- **Garbage Content Cleanup**: Automatically cleans up training data residue from model output

### Automatic Retry Mechanism
- **Dynamic Parameter Adjustment**: Automatically adjusts temperature, frequency_penalty, and other parameters based on translation failure reasons
- **Timeout Retry**: Automatic retry on API request timeout
- **Maximum Retry Limit**: Configurable maximum retry count

### Text Processing
- **Special Character Handling**: Automatically handles「」quotation marks to maintain format consistency
- **Punctuation Synchronization**: Automatically synchronizes ending punctuation between original and translated text, including `……` and `...`
- **Short Text Pass-through**: Returns very short texts that are mostly Kanji, numbers, or symbols as-is to avoid unnecessary retries
- **Think Tag Cleanup**: Automatically removes `<think>` tag content from model output
- **Configurable Newline Handling**: Supports `escape`, `keep`, and `split_lines` modes

## Requirements

- Python 3.7+
- A running SakuraLLM or OpenAI API-compatible translation service

## Installation

### 1. Install Dependencies

```bash
pip install flask gevent requests
```

### 2. Configure the Service

Edit the configuration section in `SakuraLLM.py`:

```python
# API Configuration
Base_url = "http://127.0.0.1:8080"  # API request URL
API_Key = ""  # API key, fill in when authentication is required; leave empty to skip Authorization header
Custom_Headers = {
    # "reasoning_effort": "low",  # You can place it here for convenience; it will be moved into the request body automatically
    # "X-Your-Header": "your-value",
}
Model_Type = "GalTransl-v4-4B-2601"  # Model name
Request_Timeout = 20  # Request timeout in seconds
Newline_Mode = "escape"  # Newline handling: escape / keep / split_lines

# Model Parameters
default_model_params = {
    "temperature": 0.3,  # Recommended for v3
    "max_tokens": 2048,
    "top_p": 0.8,  # Recommended for v3
    "frequency_penalty": 0.0,
}
```

If you want to further customize translation style, terminology constraints, or tone, you can continue editing `system_prompt`.

### 3. Start the Service

```bash
python SakuraLLM.py
```

> The service will listen on `http://127.0.0.1:4000` after startup.

## Usage

### API Endpoints

- **Home**: `GET /` - Display service status
- **Translate**: `GET /translate?text=your_text` - Translate the specified text

### Configure XUnity.AutoTranslator

Add the following configuration to `AutoTranslatorConfig.ini`:

```ini
[Service]
Endpoint=CustomTranslate
FallbackEndpoint=

[Custom]
Url=http://127.0.0.1:4000/translate
```

> After configuration, XUnity.AutoTranslator will send source text to this service through `GET /translate?text=...`.

## Configuration Reference

All options below are defined in the configuration section near the top of `SakuraLLM.py` and can be edited directly.

### API Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `Base_url` | Upstream SakuraLLM / OpenAI-compatible API service URL | `http://127.0.0.1:8080` |
| `API_Key` | API key; when empty, no `Authorization` header is sent | `""` |
| `Custom_Headers` | Extra request headers; `reasoning_effort` will be moved into the request body automatically | `{}` |
| `Model_Type` | Model name used in requests | `GalTransl-v4-4B-2601` |
| `Request_Timeout` | Timeout for a single API request in seconds | `20` |

### Model Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `temperature` | Controls output randomness; lower values = more stable | 0.3 |
| `max_tokens` | Maximum output tokens | 2048 |
| `top_p` | Nucleus sampling parameter | 0.8 |
| `frequency_penalty` | Frequency penalty to reduce repetition | 0.0 |

### Newline Handling

| Parameter | Description | Default |
|-----------|-------------|---------|
| `Newline_Mode` | `escape`: translate as a whole after escaping newlines; `keep`: translate as a whole while preserving real newlines; `split_lines`: translate each line separately and rejoin | `escape` |

#### Mode suggestions
- `escape`: keeps the original default behavior and is the safest starting point
- `keep`: useful when you want the model to consider multi-line context as a whole
- `split_lines`: useful for menus, short UI strings, or clearly separated lines

### Translation Quality Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `repeat_count` | Threshold for consecutive repetition detection | 8 |
| `max_retries` | Maximum retry attempts | 3 |
| `Request_Timeout` | API request timeout (seconds) | 20 |

### Built-in Behaviors

The following behaviors are currently implemented in code and work without extra configuration:

- Detects empty translations, echoed source text, prompt echo, refusal-style replies, and Japanese characters in output
- Cleans `<think>` tags and some training-data residue from model output automatically
- Returns very short texts that are mostly Kanji, numbers, or symbols as-is
- Synchronizes `「」` quotation marks and common sentence-ending punctuation automatically
- Adjusts `temperature` and `frequency_penalty` automatically when abnormal repetition is detected

## Log Output

The service outputs the following colored logs during operation:

- 🔵 **[原文]**: Received original Japanese text
- 🟢 **[译文]**: Successfully translated result
- 🟡 **[WARN]**: Translation quality warnings (repetition, contains Japanese, etc.)
- 🔴 **[ERROR]**: Translation failure or API errors

## Notes

1. Ensure SakuraLLM or a compatible translation API service is running
2. Verify that `Base_url` is correctly pointing to your model service address
3. If you encounter translation quality issues, try adjusting `temperature` and `top_p` parameters
4. SakuraLLM v3 or newer model versions are recommended
5. For very short texts that are pure Kanji or mostly Kanji, the service may return the original text directly; this is expected behavior
6. Tested on laptop RTX 4070: GalTransl-v4-4B-2601 model runs fast enough for real-time translation (RTX 4060/4060 Ti should have similar performance)

## Acknowledgments

- Thanks to [SakuraLLM](https://github.com/SakuraLLM/Sakura-13B-Galgame) for the translation model
- Thanks to [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator) for the game translation framework
- Thanks to [as176590811/XUnity.AutoTranslator-chatgpt](https://github.com/as176590811/XUnity.AutoTranslator-chatgpt) for the original code
- Thanks to [SKIPPINGpetticoatconvent/XUnity.AutoTranslator-ollama](https://github.com/SKIPPINGpetticoatconvent/XUnity.AutoTranslator-ollama) for code modifications
- Thanks to [PiDanShouRouZhouXD/Sakura_Launcher_GUI](https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI) for the Sakura Launcher