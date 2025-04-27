import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple, Optional
import string

# 加载环境变量
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 验证 API 密钥是否存在
if not DEEPSEEK_API_KEY:
    print("警告: DEEPSEEK_API_KEY 未设置，请检查 .env 文件")
    DEEPSEEK_AVAILABLE = False
else:
    try:
        from openai import OpenAI
        # 配置 DeepSeek 客户端
        deepseek_client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",  # 使用 v1 路径以保持兼容性
            timeout=150
        )
        # 测试连接
        test_response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        DEEPSEEK_AVAILABLE = True
        print("DeepSeek API 连接测试成功")
    except Exception as e:
        print(f"DeepSeek 客户端初始化失败: {str(e)}")
        DEEPSEEK_AVAILABLE = False
        deepseek_client = None

def classify_input_complexity(query: str) -> str:
    """
    使用DeepSeek-V3模型分析查询复杂度
    返回'easy'或'hard'
    """
    if not DEEPSEEK_AVAILABLE:
        print("DeepSeek不可用，默认返回'hard'")
        return "hard"
        
    prompt = (
        "你是一个专门判断查询复杂度的助手。分析以下查询，判断其复杂度。\n\n"
        "判断标准：\n"
        "- Easy: 简单的定义类、常识类问题，不需要复杂推理或专业知识\n"
        "- Hard: 需要深入理解、多步骤推理、专业知识或古汉语相关的复杂问题\n\n"
        f"查询: {query}\n\n"
        "只返回'Easy'或'Hard'，不要有任何解释："
    )
    
    try:
        print(f"开始分析查询复杂度，查询内容: {query}")  # 添加日志
        response = deepseek_client.chat.completions.create(
            model='deepseek-chat',
            messages=[
                {'role': 'system', 'content': '你是一个严格按照规则输出的AI助手'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0,
            max_tokens=5
        )
        classification = response.choices[0].message.content.strip().lower()
        print(f"DeepSeek返回的原始分类结果: {classification}")  # 添加日志
        
        # 严格验证返回值
        if classification not in ['easy', 'hard']:
            print(f"分类结果不符合预期，默认设为'hard': {classification}")  # 添加日志
            return 'hard'
            
        print(f"最终确定的复杂度: {classification}")  # 添加日志
        return classification
        
    except Exception as e:
        print(f'分类过程发生错误: {str(e)}')  # 添加错误日志
        return 'hard'

def process_with_traditional_culture_view(query: str) -> str:
    """
    使用DeepSeek-V3处理查询，提供传统文化视角的分析
    """
    if not DEEPSEEK_AVAILABLE:
        return "DeepSeek模型不可用，请检查API密钥和网络连接"
    
    try:
        # 构建提示词
        prompt = f"""你现在是一个古汉语和中国传统文化专家。请分析以下问题，提供相关的见解和知识：

{query}

请从传统文化和古汉语的角度提供详细、准确的回答。尽量引用相关典籍和传统文化知识支持你的观点。"""
        
        # 生成回答
        response = deepseek_client.chat.completions.create(
            model='deepseek-chat',
            messages=[
                {'role': 'system', 'content': '你是一个专精于古汉语和中国传统文化的AI助手'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        return response.choices[0].message.content.strip()
            
    except Exception as e:
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"传统文化视角处理错误: {error_msg}")
        return f"处理错误: {error_msg}"

def process_with_deepseek(query: str) -> str:
    """
    使用DeepSeek-V3模型处理查询
    返回模型的分析和回答
    """
    if not DEEPSEEK_AVAILABLE:
        return "DeepSeek模型不可用，请检查API密钥和网络连接"
        
    try:
        prompt = f"""请分析以下问题，提供详细的思考过程和逻辑推理：

{query}

请分步骤思考，先分析问题的关键点，然后给出清晰的解答。"""
        
        response = deepseek_client.chat.completions.create(
            model='deepseek-chat',  # DeepSeek-V3模型
            messages=[
                {'role': 'system', 'content': '你是一个专注于逻辑分析和推理的AI助手'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"DeepSeek模型处理错误: {error_msg}")
        return f"DeepSeek模型处理错误: {error_msg}"

def create_combined_prompt(query: str, traditional_culture_response: str, deepseek_response: str) -> str:
    """
    创建结合了两个辅助模型输出的提示词
    返回用于主模型的最终提示词
    """
    return f"""你是一个强大的人工智能助手，专长于中国传统文化和复杂问题的解决。用户提出了以下问题：

{query}

以下是关于该问题的两种分析视角：

【传统文化视角】：
{traditional_culture_response}

【逻辑分析视角】：
{deepseek_response}

请综合以上两种视角，提供一个全面、权威、逻辑缜密的回答。需要注意：
1. 合理融合两种视角的优点
2. 确保回答的准确性和相关性
3. 适当引用古籍或相关资料支持你的观点
4. 保持语言的流畅和易于理解

你的回答："""