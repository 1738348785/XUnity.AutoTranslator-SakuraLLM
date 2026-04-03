# XUnity.AutoTranslator-SakuraLLM GUI

这是 `XUnity.AutoTranslator-SakuraLLM` 的图形界面版本。
GUI 版本，它可以直接在窗口里完成配置、启动、测试和看日志，适合日常本地使用。

## 这个版本能做什么

- 直接在界面里填写接口地址、模型名、端口等配置
- 调整常用请求参数
- 编辑系统提示词
- 使用提示词预设
- 编辑自定义请求头 JSON
- 调整 `reasoning_effort`
- 保存 / 导入 / 导出配置
- 启动 / 停止本地翻译服务
- 在界面里测试翻译
- 查看运行日志
- 最小化到系统托盘

## 适合谁用

如果你是下面这种情况，这个版本会更方便：

- 不想手动改 Python 文件
- 不想每次都用命令行启动
- 想更直观地改配置
- 想先在本地测试翻译是否正常
- 想要一个更像桌面工具的使用方式

## 使用前准备

你需要先准备好：

- Python 运行环境（建议 3.10 及以上）
- 一个可用的 SakuraLLM 或兼容 OpenAI API 的上游接口
- Windows 系统（当前主要按 Windows 使用场景适配）

## 安装依赖

在项目目录执行：

```bash
python -m pip install -r requirements.txt
```

## 启动程序

```bash
python app.py
```

启动后会打开图形界面。

## 怎么使用

一般按这个顺序就行：

1. 填写上游接口地址 `Base URL`
2. 填写模型名称
3. 设置本地监听端口
4. 按需要调整超时、温度、`top_p` 等参数
5. 如果有额外请求头，就在自定义请求头里填 JSON
6. 如果需要，可以设置 `reasoning_effort`
7. 修改提示词，或者直接套用预设
8. 点击“保存配置”
9. 点击“启动服务”
10. 去“翻译测试”页面试一下是否能正常返回结果

## 怎么和 XUnity.AutoTranslator 对接

在 `AutoTranslatorConfig.ini` 里这样写：

```ini
[Service]
Endpoint=CustomTranslate
FallbackEndpoint=

[Custom]
Url=http://127.0.0.1:4000/translate
```

如果你在 GUI 里改了本地端口，这里的地址也要一起改。

## 自定义请求头示例

如果你的上游接口需要额外参数，可以这样写：

```json
{
  "reasoning_effort": "low"
}
```

如果你已经在界面里单独设置了 `reasoning_effort`，一般就不用再重复写。

## 配置保存在什么地方

程序默认会把配置保存到：

```text
data/config.json
```

如果你用的是打包后的 `.exe`，也会优先读取和保存到程序目录下的 `data/config.json`。

## 分支说明

仓库目前这样：

- `main`：原始主线
- `gui-main`：GUI 版本分支
