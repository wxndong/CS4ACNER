#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库迁移脚本：为ChatSession表添加title字段
"""

from flask import Flask
import sys
import os

# 添加父目录到路径，使能够正确导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import db
import sqlite3

# 创建Flask应用
app = Flask(__name__)

# 数据库配置
db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database')
db_path = os.path.join(db_dir, 'app.db')

# 确保数据库目录存在
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

def migrate():
    """为chat_sessions表添加title字段"""
    
    print(f"正在更新数据库：{db_path}")
    
    # 直接使用sqlite3连接数据库
    try:
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            print("数据库文件不存在，将创建新数据库")
            with app.app_context():
                db.create_all()
                print("数据库表已创建")
            return True
        
        # 检查字段是否已存在
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(chat_sessions)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # 检查title字段是否已存在
        if 'title' not in column_names:
            print("添加title字段到chat_sessions表...")
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN title TEXT")
            
            # 为现有会话设置默认标题
            cursor.execute("""
                UPDATE chat_sessions 
                SET title = (
                    SELECT 'Chat ' || strftime('%Y-%m-%d %H:%M', created_at) 
                    FROM chat_sessions s2 
                    WHERE s2.id = chat_sessions.id
                )
            """)
            
            conn.commit()
            print("字段添加成功！")
        else:
            print("title字段已存在，无需更新")
        
        conn.close()
        return True
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    with app.app_context():
        if migrate():
            print("数据库迁移完成")
        else:
            print("数据库迁移失败")