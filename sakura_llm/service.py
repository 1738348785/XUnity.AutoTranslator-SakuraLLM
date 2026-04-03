from flask import Flask, request, render_template_string
from gevent.pywsgi import WSGIServer

from .config import AppConfig
from .logging_bridge import LoggerBridge
from .translator import Translator


class TranslationService:
    def __init__(self, config: AppConfig, logger: LoggerBridge):
        self.config = config
        self.logger = logger
        self.translator = Translator(config, logger)
        self.app = Flask(__name__)
        self.server = None
        self._register_routes()

    def _register_routes(self):
        @self.app.route("/translate", methods=["GET"])
        def translate():
            text = request.args.get("text")
            if not text:
                return "缺少text参数", 400
            self.logger.info(f"[原文] {text}")
            translation = self.translator.handle_translation(text)
            if isinstance(translation, str):
                return translation
            return "[翻译失败] " + text, 500

        @self.app.route("/", methods=["GET"])
        def index():
            return render_template_string(
                """
                <h1>SakuraLLM 翻译服务已启动</h1>
                <p>请访问 <code>/translate?text=你的文本</code> 进行翻译</p>
                <p>当前模型: <strong>{{ model }}</strong></p>
                """,
                model=self.config.model_type,
            )

    def start(self):
        if self.server is not None:
            return
        newline_mode = self.translator.resolve_newline_mode(show_warning=True)
        self.logger.info("=" * 60)
        self.logger.info("SakuraLLM 翻译服务启动中...")
        self.logger.info(f"地址: http://127.0.0.1:{self.config.listen_port}")
        self.logger.info(f"模型: {self.config.model_type}")
        self.logger.info(f"换行模式: {newline_mode}")
        self.logger.info(
            f"参数: temperature={self.config.temperature}, top_p={self.config.top_p}"
        )
        self.logger.info("=" * 60)
        self.server = WSGIServer(
            ("127.0.0.1", self.config.listen_port),
            self.app,
            log=None,
            error_log=None,
        )

    def serve_forever(self):
        if self.server is None:
            self.start()
        self.server.serve_forever()

    def stop(self):
        if self.server is not None:
            self.server.stop(timeout=1)
            self.logger.info("服务器已停止")
            self.server = None
