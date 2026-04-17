# XUnity.AutoTranslator-SakuraLLM GUI

[English](https://github.com/1738348785/XUnity.AutoTranslator-SakuraLLM/blob/gui-main/README.en.md) · 简体中文

`XUnity.AutoTranslator-SakuraLLM` 的图形界面版本。在窗口里完成**配置、启动、测试、看日志**，开着挂机用。

![界面预览](页面截图.png)

## 特性

- 🖥️ **全图形化配置**：接口地址、模型、端口、请求头、提示词，全部点点填填
- ⚡ **真正的并发翻译**：gevent 协程 + 可调并发上限，场景切换不再"一行行冒字幕"
- 💾 **LRU 翻译缓存**：重复文案（菜单、系统提示）毫秒级命中，节省显卡算力
- 🔀 **并发合并**：同一瞬间多个相同请求只跑一次，其余共享结果
- 🩺 **后端健康检查**：服务启动后立刻探活，配置错误当场暴露
- 🎛️ **参数实时生效**：改 `max_concurrency` 不用重启服务
- 💬 **提示词预设**：一键切换多套翻译风格
- 🌐 **中英双语界面** + 系统托盘最小化

## 快速开始

### 方式一：下载 exe（推荐）

从 [Releases](https://github.com/1738348785/XUnity.AutoTranslator-SakuraLLM/releases) 下载最新的 `XUnity.AutoTranslator-SakuraLLM GUI.exe`，双击运行即可。

### 方式二：源码运行

```bash
pip install -r requirements.txt
python app.py
```

> 需要 Python 3.10+。推荐 Windows。

## 配置流程

1. 填 **Base URL**（SakuraLLM 或任何 OpenAI 兼容接口，如 `http://127.0.0.1:8080`）
2. 填 **模型名称**
3. 设置 **本地监听端口**（默认 4000）
4. 按需调温度、Top-P、最大并发数等
5. 点 **保存配置** → **启动服务**
6. 到 **翻译测试** 页面验证输出

## 对接 XUnity.AutoTranslator

编辑 `AutoTranslatorConfig.ini`：

```ini
[Service]
Endpoint=CustomTranslate
FallbackEndpoint=

[Custom]
Url=http://127.0.0.1:4000/translate
```

端口若有修改，同步改这里的 `Url`。

## 关键参数说明

| 参数 | 说明 | 推荐值 |
|---|---|---|
| `temperature` | 采样温度，越低越稳定 | `0.1 - 0.5` |
| `top_p` | 核采样阈值 | `0.8` |
| `max_tokens` | 单次生成上限 | `2048` |
| `max_concurrency` | 最大并发请求数（**运行时可调**） | `2 - 8`，看后端承受力 |
| `max_retries` | 翻译不合格时重试次数 | `3` |
| `repeat_count` | 重复检测阈值 | `8` |

## 自定义请求头

上游需要额外参数时（如 DeepSeek-R1 的 `reasoning_effort`），可以单独在"配置中心"里设置；也可以通过自定义请求头 JSON 注入：

```json
{
  "reasoning_effort": "low"
}
```

两处设置了会以自定义请求头为准。

## 配置文件位置

- **源码运行**：项目目录下 `data/config.json`
- **打包 exe**：`.exe` 同级目录下 `data/config.json`

写入采用原子替换，异常断电不会损坏配置。

## 常见问题

**翻译失败、延迟高？**
- 在"配置中心"把 `max_concurrency` 开大（4-8）
- 确认后端（llama.cpp / KoboldCpp 等）已启动——启动服务后日志里会有"后端连通正常"或"后端不可达"提示

**端口被占？**
- 换一个端口，或关掉占用端口的其它程序。失败原因会实时在日志里显示。

**打包 exe 启动慢？**
- 首次解压到临时目录，后续启动会快。

## 分支

- `main`：原始主线
- `gui-main`：GUI 版本（本分支）
