from flask import Blueprint, request, jsonify
import jwt
import datetime
print(jwt.__file__) # 打印 jwt 模块的加载路径
from functools import wraps
from database.models import User, db
import logging
# 移除这个导入，因为我们不需要在蓝图级别设置 CORS
# from flask_cors import CORS

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
# 移除这一行，避免重复设置 CORS
# CORS(auth_bp)

# JWT配置
JWT_SECRET_KEY = 'your-secret-key'  # 在生产环境中应该使用环境变量存储
JWT_EXPIRATION_HOURS = 24

def create_token(user_id):
    """创建JWT token"""
    try:
        payload = {
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
        # 确保返回的是字符串，兼容不同 PyJWT 版本
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token
    except Exception as e:
        logger.error(f"创建token时出错: {str(e)}")
        raise

def token_required(f):
    """验证token的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '缺少token'}), 401
        try:
            token = token.split(' ')[1]  # Bearer token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': '无效的token'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'token已过期'}), 401
        except Exception as e:
            logger.error(f"验证token时出错: {str(e)}")
            return jsonify({'message': '无效的token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        logger.debug("开始处理登录请求")
        data = request.get_json()
        logger.debug(f"接收到的数据: {data}")

        if not data:
            logger.error("没有接收到JSON数据")
            return jsonify({'message': '无效的请求数据'}), 400

        username = data.get('username')
        password = data.get('password')

        logger.debug(f"尝试登录用户: {username}")

        if not username or not password:
            logger.error("用户名或密码为空")
            return jsonify({'message': '用户名和密码不能为空'}), 400

        try:
            user = User.query.filter_by(username=username).first()
            logger.debug(f"查询到的用户: {user}")
        except Exception as e:
            logger.error(f"数据库查询出错: {str(e)}")
            return jsonify({'message': '服务器错误1'}), 500

        if not user:
            logger.error(f"用户不存在: {username}")
            return jsonify({'message': '用户名或密码错误'}), 401

        try:
            if not user.check_password(password):
                logger.error(f"密码错误: {username}")
                return jsonify({'message': '用户名或密码错误'}), 401
        except Exception as e:
            logger.error(f"密码验证出错: {str(e)}")
            return jsonify({'message': '服务器错误2'}), 500

        try:
            token = create_token(user.id)
            logger.debug(f"生成的token: {token[:10]}...")  # 只记录token的前10个字符
        except Exception as e:
            logger.error(f"生成token出错: {str(e)}")
            return jsonify({'message': '服务器错误3'}), 500

        try:
            # 更新最后登录时间
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            logger.debug(f"更新最后登录时间成功")
        except Exception as e:
            logger.error(f"更新最后登录时间失败: {str(e)}")
            db.session.rollback()
            # 这里我们不返回错误，因为登录本身是成功的

        response_data = {
            'token': token,
            'username': user.username
        }
        logger.debug(f"登录成功，返回数据: {response_data}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"登录过程中出现未知错误: {str(e)}")
        db.session.rollback()
        return jsonify({'message': '登录失败，请稍后重试'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        logger.debug("开始处理注册请求")
        data = request.get_json()
        logger.debug(f"接收到的数据: {data}")

        if not data:
            logger.error("没有接收到JSON数据")
            return jsonify({'message': '无效的请求数据'}), 400

        username = data.get('username')
        password = data.get('password')

        logger.debug(f"尝试注册用户: {username}")

        if not username or not password:
            logger.error("用户名或密码为空")
            return jsonify({'message': '用户名和密码不能为空'}), 400

        if User.query.filter_by(username=username).first():
            logger.error(f"用户名已存在: {username}")
            return jsonify({'message': '用户名已存在'}), 400

        try:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            logger.debug(f"注册成功: {username}")
            return jsonify({'message': '注册成功'}), 201
        except Exception as e:
            logger.error(f"创建用户时出错: {str(e)}")
            db.session.rollback()
            return jsonify({'message': '注册失败'}), 500

    except Exception as e:
        logger.error(f"注册过程中出现未知错误: {str(e)}")
        db.session.rollback()
        return jsonify({'message': '注册失败'}), 500

@auth_bp.route('/user', methods=['GET'])
@token_required
def get_user(current_user):
    return jsonify(current_user.to_dict()), 200