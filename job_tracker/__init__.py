from flask import Flask

from .config import Config
from .routes import main


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)
    app.register_blueprint(main)
    return app
