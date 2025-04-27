from flask import Flask, jsonify, request
from flask_cors import CORS
from routes.ner_routes import ner_bp
from routes.chat_routes import chat_bp
from routes.auth_routes import auth_bp
from database.models import db
import os

app = Flask(__name__)

# 配置CORS
# 方法1：使用 flask_cors 扩展（推荐）
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8081", "http://127.0.0.1:8081"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# 数据库配置和其他设置...
# 确保数据库目录存在
db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# 数据库配置
db_path = os.path.join(db_dir, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# 初始化数据库
db.init_app(app)

# 创建所有数据库表
with app.app_context():
    try:
        db.create_all()
        print("数据库表创建成功")
    except Exception as e:
        print(f"创建数据库表时出错: {str(e)}")


# 注册路由
app.register_blueprint(ner_bp, url_prefix="/api")
app.register_blueprint(chat_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api/auth")

# 在创建Flask app后添加
app.config['JSON_AS_ASCII'] = False  # 确保JSON响应不使用ASCII编码
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# 移除这个 after_request 处理器，因为我们已经使用 flask_cors 扩展设置了 CORS
# @app.after_request
# def after_request(response):
#     origin = request.headers.get('Origin')
#     if origin in ["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8081", "http://127.0.0.1:8081"]:
#         response.headers.add('Access-Control-Allow-Origin', origin)
#         response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
#         response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
#         response.headers.add('Access-Control-Allow-Credentials', 'true')
#     return response

@app.route('/')
def home():
    return "CS4ACNER Backend Service is Running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)