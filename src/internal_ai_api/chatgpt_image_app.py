from .app_factory import create_proxy_app
from .config import load_settings

settings = load_settings("chatgpt-image")
app = create_proxy_app(settings)

