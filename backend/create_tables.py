#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from database.models import db, User, ChatSession, ChatMessage
import os

# 创建Flask应用
app = Flask(__name__)

# 确保数据库目录存在
db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# 数据库配置
db_path = os.path.join(db_dir, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 创建数据库表
with app.app_context():
    try:
        # 删除所有现有表并重新创建
        db.drop_all()
        db.create_all()
        print("数据库表创建成功")
    except Exception as e:
        print(f"创建数据库表时出错: {str(e)}")

if __name__ == "__main__":
    print("数据库初始化完成") 