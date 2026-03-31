from flask import Flask, request, session, redirect
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
# 计算项目根目录（向上三级：flask_app/__init__.py -> flask_app -> my_flask_app -> 项目根目录）
project_root = Path(__file__).parent.parent.parent
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

env_path = project_root / '.env'
load_dotenv(env_path, override=True)


def setup_logging():
    """确保业务日志（logger.info）能进入 app.log。"""
    level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()

    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stdout,
        )
    else:
        root.setLevel(level)

def auth():
    # 静态文件直接放行
    if request.path.startswith('/static'):
        return

    # 登录和注册页面直接放行
    if request.path in ['/login', '/register']:
        return
    
    # 健康检查接口直接放行
    if request.path == '/api/chat/health':
        return

    # 检查用户会话
    userinfo = session.get("userinfo")

    # 如果没有用户信息，重定向到登录页
    if not userinfo:
        return redirect('/login')

def create_app():
    setup_logging()

    app = Flask(__name__)
    app.secret_key = 'aaaaaaaaaa'
    
    # 禁用Flask和Werkzeug的INFO级别日志
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)

    app.before_request(auth)

    from .views import account
    app.register_blueprint(account.ac)

    from .views import test
    app.register_blueprint(test.ts)

    from .views import main
    app.register_blueprint(main.mi)

    from .views import care_flow
    app.register_blueprint(care_flow.cf)

    # 注册心理咨询模块（EmoLLM集成）
    from .views import psychological_counseling
    app.register_blueprint(psychological_counseling.pc)

    # 注册新增会话总结Skill接口（独立目录实现，默认不影响原有问诊链路）
    try:
        from new_features.session_summary_skill.api import session_summary_bp

        app.register_blueprint(session_summary_bp)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "session_summary_skill blueprint not loaded: %s", exc
        )

    try:
        from new_features.scale_assessment.api import scale_assessment_bp

        app.register_blueprint(scale_assessment_bp)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "scale_assessment blueprint not loaded: %s", exc
        )

    return app
