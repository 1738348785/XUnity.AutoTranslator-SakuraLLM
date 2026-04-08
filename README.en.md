# XUnity.AutoTranslator-SakuraLLM GUI

[简体中文](https://github.com/1738348785/XUnity.AutoTranslator-SakuraLLM/blob/gui-main/README.md)

This is the GUI edition of `XUnity.AutoTranslator-SakuraLLM`.

The GUI version lets you configure, start, test, and inspect logs directly from a desktop window, which is more convenient for everyday local use.

## What This Version Can Do

- Fill in connection settings such as API endpoint, model name, and local port directly in the GUI
- Adjust common request parameters
- Edit the system prompt
- Use prompt presets
- Edit custom request headers in JSON format
- Adjust `reasoning_effort`
- Save / import / export configuration
- Start / stop the local translation service
- Test translation directly in the GUI
- View runtime logs
- Minimize to the system tray

## Who This Is For

This version is more convenient if you:

- do not want to edit Python files manually
- do not want to start the tool from the command line every time
- want a more visual way to change settings
- want to verify translation locally first
- prefer a desktop-tool workflow

## Requirements

Prepare the following before use:

- Python runtime environment, preferably 3.10 or newer
- A working SakuraLLM endpoint or another upstream endpoint compatible with the OpenAI API
- Windows system environment, which is the primary target platform for this GUI build

## Install Dependencies

Run this in the project directory:

```bash
python -m pip install -r requirements.txt
```

## Start the App

```bash
python app.py
```

After startup, the graphical interface will open.

## Basic Usage

A typical flow looks like this:

1. Fill in the upstream endpoint in `Base URL`
2. Fill in the model name
3. Set the local listening port
4. Adjust timeout, temperature, `top_p`, and other parameters as needed
5. If extra headers are required, fill them in as JSON in the custom headers section
6. Set `reasoning_effort` if needed
7. Edit the prompt or apply a preset directly
8. Click `Save Config`
9. Click `Start Service`
10. Open the `Translation Test` page and verify that requests return normal results

## How To Connect With XUnity.AutoTranslator

Set `AutoTranslatorConfig.ini` like this:

```ini
[Service]
Endpoint=CustomTranslate
FallbackEndpoint=

[Custom]
Url=http://127.0.0.1:4000/translate
```

If you change the local listening port in the GUI, update the address here as well.

## Custom Header Example

If your upstream endpoint requires extra parameters, you can write them like this:

```json
{
  "reasoning_effort": "low"
}
```

If you already set `reasoning_effort` separately in the GUI, you usually do not need to repeat it here.

## Where The Configuration Is Saved

By default, the application saves its configuration to:

```text
data/config.json
```

If you are using the packaged `.exe`, it will also prefer reading and writing `data/config.json` in the application directory.

## Branch Notes

The repository is currently organized like this:

- `main`: original mainline branch
- `gui-main`: GUI branch
