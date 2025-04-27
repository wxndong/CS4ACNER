from flask import Blueprint, request, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import os
from uuid import uuid4
import bleach
from dotenv import load_dotenv
import json
from utils import (
    deepseek_client,
    DEEPSEEK_AVAILABLE,
    classify_input_complexity,
    process_with_traditional_culture_view,
    process_with_deepseek,
    create_combined_prompt
)
# 导入数据库模型
from database.models import db, ChatSession, ChatMessage
from datetime import datetime

# 加载环境变量
load_dotenv()

# 创建蓝图
chat_bp = Blueprint("chat", __name__)

# 速率限制器
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# 配置API密钥
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 导入OpenAI客户端 - 必要时使用
try:
    from openai import OpenAI
    # 配置DeepSeek客户端
    deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com", timeout=150)
    deepseek_r1_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com", timeout=150)
    DEEPSEEK_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"DeepSeek客户端初始化失败: {str(e)}")
    DEEPSEEK_AVAILABLE = False

@chat_bp.route("/session", methods=["GET"])
def create_session():
    """生成新的会话 ID 并在数据库中创建会话记录"""
    session_id = str(uuid4())
    
    # 在数据库中创建新会话，使用默认标题
    default_title = f"会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    new_session = ChatSession(id=session_id, title=default_title)
    db.session.add(new_session)
    
    try:
        db.session.commit()
        return jsonify({"session_id": session_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"创建会话失败: {str(e)}"}), 500

@chat_bp.route("/chat", methods=["POST"])
@limiter.limit("10 per minute")
def chat():
    try:
        # 确保请求使用UTF-8编码解析
        request.charset = 'utf-8'
        data = request.get_json(force=True)  # 强制使用UTF-8解析
        
        if not data or "query" not in data or "session_id" not in data:
            return jsonify({"reply": "请求数据无效，请提供 query 和 session_id。"}), 400

        # 确保输入是UTF-8编码
        user_input = bleach.clean(str(data["query"]).encode('utf-8').decode('utf-8'))
        session_id = str(data["session_id"]).encode('utf-8').decode('utf-8')
        
        # 是否使用动态路由 (可选参数)
        use_dynamic_routing = data.get("use_dynamic_routing", True)
        # 是否使用流式输出 (可选参数)
        use_streaming = data.get("streaming", False)

        # 验证输入长度
        if not (1 <= len(user_input) <= 500):
            return jsonify({"reply": "输入无效，请输入1-500字符的问题。"}), 400

        # 从数据库获取会话
        chat_session = ChatSession.query.get(session_id)
        if not chat_session:
            # 如果会话不存在，创建新会话
            chat_session = ChatSession(id=session_id)
            db.session.add(chat_session)
            db.session.commit()
        
        # 从数据库加载历史消息
        chat_history = []
        db_messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
        for msg in db_messages:
            chat_history.append({"role": msg.role, "content": msg.content})
        
        # 添加用户消息到数据库
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_input
        )
        db.session.add(user_message)
        db.session.commit()
        
        # 更新内存中的聊天历史用于API调用
        chat_history.append({"role": "user", "content": user_input})
        
        # 系统提示词
        system_prompt = "你是一个古汉语知识助手，请根据提问进行回答。"
        
        # 判断是否使用动态路由
        routing_info = None
        if use_dynamic_routing and DEEPSEEK_AVAILABLE:
            # 使用动态路由机制
            reply_text, routing_info = process_with_dynamic_routing(user_input, chat_history, use_streaming)
        else:
            # 使用原有API（默认方案）
            reply_text = process_with_original_api(user_input, chat_history, system_prompt)
            
        # 添加AI回复到数据库
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply_text,
            routing_info=routing_info
        )
        db.session.add(assistant_message)
        
        # 更新会话的最后活动时间
        chat_session.last_activity = db.func.current_timestamp()
        db.session.commit()
        
        # 构建响应
        response_data = {
            "reply": reply_text.encode('utf-8').decode('utf-8')  # 确保Unicode编码
        }
        
        # 如果使用了动态路由，添加路由信息
        if routing_info:
            response_data["routing_info"] = routing_info
            
        # 设置UTF-8编码的响应头
        response = jsonify(response_data)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"reply": f"服务器错误: {str(e)}"}), 500

def process_with_dynamic_routing(query, chat_history, streaming=False):
    """
    使用动态路由机制处理查询
    返回: (回复文本, 路由信息)
    """
    try:
        # 使用 DeepSeek-V3 判断查询复杂度
        complexity = classify_input_complexity(query)
        print(f"查询复杂度: {complexity}")
        
        # 准备路由信息
        routing_info = {
            "complexity": complexity,
            "model_used": "deepseek-reasoner" if complexity == "hard" else "deepseek-v3"
        }
        
        if complexity == "easy":
            # 简单查询直接使用 DeepSeek-V3 处理
            print("使用 DeepSeek-V3 直接回答")
            response = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专注于古汉语和中国传统文化的AI助手"},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=1000,
                stream=False
            )
            return response.choices[0].message.content, routing_info
            
        else:
            # 复杂查询使用多模型协作
            print("使用复合模型处理复杂查询")
            
            # 1. 传统文化视角处理
            traditional_culture_response = process_with_traditional_culture_view(query)
            
            # 2. DeepSeek-V3 逻辑分析视角处理
            deepseek_response = process_with_deepseek(query)
            
            # 3. 使用 DeepSeek-R1 作为主力模型
            combined_prompt = create_combined_prompt(query, traditional_culture_response, deepseek_response)
            
            response = deepseek_client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[{"role": "user", "content": combined_prompt}],
                temperature=0.7,
                max_tokens=2000,
                stream=False
            )
            
            # 获取推理过程和最终答案
            final_response = response.choices[0].message
            reasoning = final_response.reasoning_content if hasattr(final_response, 'reasoning_content') else ""
            answer = final_response.content
            
            # 返回完整回答
            return (f"{answer}\n\n推理过程：\n{reasoning}" if reasoning else answer), routing_info
            
    except Exception as e:
        print(f"动态路由处理错误: {str(e)}")
        # 出错时，返回没有路由信息的结果
        return process_with_original_api(query, chat_history, "你是一个古汉语知识助手，请根据提问进行回答。"), None

def process_with_original_api(query, chat_history, system_prompt):
    """
    使用原有API处理查询
    """
    try:
        if not DEEPSEEK_API_KEY:
            return "API 密钥未配置，请检查 .env 文件"
            
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "ClassicalChineseAssistant/1.0",
            "Accept": "application/json; charset=utf-8",
            "Accept-Charset": "utf-8"
        }

        payload = {
            "model": "deepseek-chat",  # 使用最新的 DeepSeek-V3
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",  # 使用 v1 路径
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 401:
            return "API 认证失败，请检查 API 密钥是否正确"
        
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "无有效回复")
        return content.encode('utf-8').decode('utf-8')
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if "401" in error_msg:
            return "API 认证失败，请检查 API 密钥是否正确"
        elif "timeout" in error_msg.lower():
            return "请求超时，请稍后重试"
        else:
            return f"API 请求错误: {error_msg}"
    except Exception as e:
        return f"处理请求时发生错误: {str(e)}"

# 更新路由状态检查
@chat_bp.route("/routing_status", methods=["GET"])
def get_routing_status():
    """获取动态路由机制状态"""
    status = {
        "deepseek_available": DEEPSEEK_AVAILABLE,
        "dynamic_routing_enabled": DEEPSEEK_AVAILABLE,
    }
    return jsonify(status)

@chat_bp.route("/clear_history", methods=["POST"])
def clear_history():
    """清空指定会话的历史记录"""
    data = request.get_json()
    if not data or "session_id" not in data:
        return jsonify({"success": False, "message": "请求数据无效，请提供session_id。"}), 400
        
    session_id = data["session_id"]
    
    try:
        # 从数据库中删除会话消息
        ChatMessage.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        return jsonify({"success": True, "message": "会话历史已清空"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"清空历史记录失败: {str(e)}"}), 500

# 添加获取历史记录的接口
@chat_bp.route("/history", methods=["GET"])
def get_history():
    """获取指定会话的历史记录"""
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"success": False, "message": "请求数据无效，请提供session_id。"}), 400
    
    try:
        # 从数据库中查询会话消息
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
        
        # 转换为前端所需格式
        history = []
        for msg in messages:
            message_data = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.routing_info:
                message_data["routingInfo"] = {
                    "complexity": msg.routing_info.get("complexity", ""),
                    "model_used": msg.routing_info.get("model_used", "")
                }
            history.append(message_data)
            
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取历史记录失败: {str(e)}"}), 500

# 添加会话列表接口（可选，用于管理多个会话）
@chat_bp.route("/sessions", methods=["GET"])
def get_sessions():
    """获取所有会话列表"""
    try:
        # 查询活跃的会话
        sessions = ChatSession.query.filter_by(is_active=True).order_by(ChatSession.last_activity.desc()).all()
        
        # 转换为前端所需格式
        session_list = []
        for session in sessions:
            # 使用会话的标题字段
            title = session.title
            
            # 如果没有标题，则使用第一条用户消息作为备选标题
            if not title:
                first_message = ChatMessage.query.filter_by(session_id=session.id, role="user").order_by(ChatMessage.created_at).first()
                title = first_message.content[:30] + "..." if first_message and len(first_message.content) > 30 else "新会话"
                # 更新会话标题
                session.title = title
                db.session.commit()
            
            session_list.append({
                "id": session.id,
                "title": title,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat()
            })
            
        return jsonify({"success": True, "sessions": session_list})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取会话列表失败: {str(e)}"}), 500

# 添加删除会话的接口
@chat_bp.route("/delete_session", methods=["POST"])
def delete_session():
    """删除指定的会话"""
    data = request.get_json()
    if not data or "session_id" not in data:
        return jsonify({"success": False, "message": "请求数据无效，请提供session_id。"}), 400
        
    session_id = data["session_id"]
    
    try:
        # 从数据库中查找会话
        session = ChatSession.query.get(session_id)
        if not session:
            return jsonify({"success": False, "message": "会话不存在"}), 404
            
        # 删除会话及其所有消息（级联删除）
        db.session.delete(session)
        db.session.commit()
        return jsonify({"success": True, "message": "会话已删除"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"删除会话失败: {str(e)}"}), 500

# 添加重命名会话的接口
@chat_bp.route("/rename_session", methods=["POST"])
def rename_session():
    """重命名指定会话，直接修改session的title字段"""
    data = request.get_json()
    if not data or "session_id" not in data or "title" not in data:
        return jsonify({"success": False, "message": "请求数据无效，请提供session_id和title。"}), 400
        
    session_id = data["session_id"]
    new_title = data["title"].strip()
    
    if not new_title:
        return jsonify({"success": False, "message": "标题不能为空"}), 400
    
    try:
        # 从数据库中查找会话
        session = ChatSession.query.get(session_id)
        if not session:
            return jsonify({"success": False, "message": "会话不存在"}), 404
        
        # 直接更新会话标题
        session.title = new_title
        db.session.commit()
        return jsonify({"success": True, "message": "会话已重命名"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"重命名会话失败: {str(e)}"}), 500