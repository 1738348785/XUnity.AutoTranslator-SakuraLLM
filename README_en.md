# SakuraLLM Translation Service

[中文版本](README_zh.md)

## Introduction

A Flask-based game translation bridge service that connects XUnity.AutoTranslator with SakuraLLM (or OpenAI API-compatible translation models) to translate Japanese text in games into Simplified Chinese.

This service is optimized for visual novel/Galgame translation, featuring intelligent translation quality control and automatic retry mechanisms.

## Features

### Translation Quality Control
- **Smart Validation**: Automatically detects translation quality issues such as empty translations, echoing original text, or containing Japanese characters
- **Repetition Detection**: Detects abnormal repeated phrases in translations and automatically adjusts parameters for retry
- **Onomatopoeia Recognition**: Intelligently identifies onomatopoeia/emotional expressions to avoid false positives on intentional repetition patterns
- **Garbage Content Cleanup**: Automatically cleans up training data residue from model output

### Automatic Retry Mechanism
- **Dynamic Parameter Adjustment**: Automatically adjusts temperature, frequency_penalty, and other parameters based on translation failure reasons
- **Timeout Retry**: Automatic retry on API request timeout
- **Maximum Retry Limit**: Configurable maximum retry count

### Text Processing
- **Special Character Handling**: Automatically handles「」quotation marks to maintain format consistency
- **Punctuation Synchronization**: Automatically synchronizes ending punctuation between original and translated text
- **Think Tag Cleanup**: Automatically removes `<think>` tag content from model output

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
Model_Type = "GalTransl-v4-4B-2601"  # Model name
Request_Timeout = 20  # Request timeout in seconds

# Translation Quality Control
repeat_count = 8  # Retry if any character/word appears consecutively >= this count
max_retries = 3  # Maximum retry attempts

# Model Parameters
default_model_params = {
    "temperature": 0.3,  # Recommended for v3
    "max_tokens": 2048,
    "top_p": 0.8,  # Recommended for v3
    "frequency_penalty": 0.0,
}
```

### 3. Start the Service

```bash
python SakuraLLM.py
```

The service will listen on `http://127.0.0.1:4000` after startup.

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

## Configuration Reference

### Model Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `temperature` | Controls output randomness; lower values = more stable | 0.3 |
| `max_tokens` | Maximum output tokens | 2048 |
| `top_p` | Nucleus sampling parameter | 0.8 |
| `frequency_penalty` | Frequency penalty to reduce repetition | 0.0 |

### Translation Quality Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `repeat_count` | Threshold for repetition detection | 8 |
| `max_retries` | Maximum retry attempts | 3 |
| `Request_Timeout` | API request timeout (seconds) | 30 |

## Log Output

The service outputs colored logs during operation:

- 🔵 **[原文]**: Received original Japanese text
- 🟢 **[译文]**: Successfully translated result
- 🟡 **[WARN]**: Translation quality warnings (repetition, contains Japanese, etc.)
- 🔴 **[ERROR]**: Translation failure or API errors

## Notes

1. Ensure SakuraLLM or a compatible translation API service is running
2. Verify that `Base_url` is correctly pointing to your model service address
3. If you encounter translation quality issues, try adjusting `temperature` and `top_p` parameters
4. SakuraLLM v3 or newer model versions are recommended
5. Tested on laptop RTX 4070: GalTransl-v4-4B-2601 model runs fast enough for real-time translation (RTX 4060/4060 Ti should have similar performance)

## Acknowledgments

- Thanks to [SakuraLLM](https://github.com/SakuraLLM/Sakura-13B-Galgame) for the translation model
- Thanks to [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator) for the game translation framework
- Thanks to [as176590811/XUnity.AutoTranslator-chatgpt](https://github.com/as176590811/XUnity.AutoTranslator-chatgpt) for the original code
- Thanks to [SKIPPINGpetticoatconvent/XUnity.AutoTranslator-ollama](https://github.com/SKIPPINGpetticoatconvent/XUnity.AutoTranslator-ollama) for code modifications
- Thanks to [PiDanShouRouZhouXD/Sakura_Launcher_GUI](https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI) for the Sakura Launcher

## License

MIT License
