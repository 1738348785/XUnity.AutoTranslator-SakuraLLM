# SakuraLLM GUI

这是 `XUnity.AutoTranslator-SakuraLLM` 的 PySide6 图形界面版。

## 当前功能

- 图形化编辑配置
- 保存到 `data/config.json`
- 支持编辑自定义请求头 JSON
- 支持导入/导出配置 JSON
- 支持编辑系统提示词
- 内置原版提示词预设
- 启动/停止本地 Flask 翻译服务
- 启动前检查本地监听端口是否被占用
- 支持最小化到系统托盘
- 查看彩色运行日志
- 在 GUI 中测试 `/translate` 接口
- 保持与 XUnity.AutoTranslator 的本地 HTTP 对接方式兼容

## 目录结构

```text
app.py
sakura_llm/
  config.py
  logging_bridge.py
  service.py
  translator.py
gui/
  main_window.py
data/
requirements.txt
```

## 安装依赖

```bash
python -m pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

## 使用方式

1. 填写上游 API 地址、模型名、端口等配置。
2. 如需附加请求头，在“自定义请求头(JSON)”中填写 JSON。
3. 如需修改翻译风格，可直接编辑“系统提示词”，或先应用“sakura预设”。
4. 点击“保存配置”。
5. 点击“启动服务”。
6. 在 XUnity.AutoTranslator 中配置：

```ini
[Service]
Endpoint=CustomTranslate
FallbackEndpoint=

[Custom]
Url=http://127.0.0.1:4000/translate
```

如果你改了监听端口，请同步修改这里的 URL。

## 自定义请求头示例

```json
{
  "reasoning_effort": "low"
}
```

## 打包建议

先使用 `onedir` 模式调试：

```bash
pyinstaller --noconfirm --windowed --onedir app.py
```

稳定后再尝试 `--onefile`。

## 说明

当前版本仍是增强中的本地版：
- 暂未加入图标和安装包
- 暂未加入自动更新
