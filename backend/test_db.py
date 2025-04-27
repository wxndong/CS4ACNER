#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from database.models import db, ChatSession, ChatMessage
import os
import uuid

# 创建Flask应用
app = Flask(__name__)

# 数据库配置
db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
db_path = os.path.join(db_dir, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

def test_chat_session():
    """测试聊天会话和消息功能"""
    with app.app_context():
        # 创建新会话
        session_id = str(uuid.uuid4())
        new_session = ChatSession(id=session_id)
        db.session.add(new_session)
        db.session.commit()
        
        print(f"创建新会话: {session_id}")
        
        # 添加用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content="子曰：学而时习之，不亦说乎？"
        )
        db.session.add(user_msg)
        db.session.commit()
        
        # 添加助手消息
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content="这句话出自《论语·学而》，意思是：孔子说：学习了知识并且能够及时复习练习，不是很愉快吗？",
            routing_info={"complexity": "easy", "model_used": "deepseek-v3"}
        )
        db.session.add(assistant_msg)
        db.session.commit()
        
        # 查询测试
        session = ChatSession.query.get(session_id)
        print(f"会话创建时间: {session.created_at}")
        
        messages = ChatMessage.query.filter_by(session_id=session_id).all()
        print(f"消息数量: {len(messages)}")
        
        for msg in messages:
            print(f"[{msg.role}] {msg.content[:30]}...")
            if msg.routing_info:
                print(f"路由信息: {msg.routing_info}")
        
        return True

if __name__ == "__main__":
    try:
        test_result = test_chat_session()
        if test_result:
            print("\n✅ 测试成功：数据库功能正常工作！")
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}") 