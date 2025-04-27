# Cs4aCNER

# 项目介绍

本项目是CurlyD的毕业设计，为了解决古汉语在命名实体识别领域、问答领域的问题，三大功能模块如下：

## 核心功能模块

### NER 模块

NER 模块负责识别古汉语文本中的命名实体，主要支持两种模型类型：

1. **古汉语历史增强模型 (模型A)**
   - 支持实体类型：NR（人名）、NS（地名）、NB（书名）、NO（官职名）、NG（国家名）、T（时间）
   - 基于 GujiRoBERTa_jian_fan 预训练模型与 CRF 结构

2. **古汉语医疗增强模型 (模型C)**
   - 支持实体类型：ZD（中医疾病）、ZZ（证候）、ZF（中药方剂）、ZP（中药饮片）、ZS（症状）、ZA（穴位）
   - 针对古代医疗文献特殊优化

特色功能：
- **大模型增强**: 通过 DeepSeek 大模型二次矫正及实体识别增强，提高少数实体及边界模糊实体的识别准确率
- **热更新**: 支持模型的动态切换
- **批量处理**: 支持文件上传和批量处理
- **结果导出**: 支持分析结果的下载和保存

### LLM问答模块

LLM问答模块实现了基于查询复杂度的动态路由机制，为用户提供智能化的古汉语问答服务。

核心特点：
- **多轮对话**: 支持上下文相关的连续对话
- **动态路由机制**: 
  - 由 DeepSeek-V3 打分模型负责复杂度评估
  - 低复杂度查询（Easy）：直接调用 DeepSeek-V3 大模型回答
  - 高复杂度查询（Hard）：使用三模型协作机制
    1. DeepSeek-V3 作为辅助模型A（传统文化视角）
    2. DeepSeek-V3 作为辅助模型B（逻辑分析视角）
    3. DeepSeek-R1 作为主力模型，综合两种视角生成最终回答
- **NER模块联动**: 用户可以选中NER分析结果中的实体直接发起提问
- **会话管理功能**：
  - **查看历史对话**：用户可以查看历史会话记录
  - **会话删除**：支持删除不再需要的会话
  - **会话重命名**：允许用户为会话添加自定义标题，便于管理
  - **会话切换**：用户可以在多个会话之间快速切换
  - **会话列表**：提供直观的会话历史管理界面

ps:2025可谓是AI Agent元年，本来想蹭一下结果没蹭到hhh

### 用户认证模块

实现了基于JWT的用户认证系统，确保系统安全性：
- 用户注册与登录
- 会话管理
- 访问控制


# 快速开始
1. 本地设置环境变量，将DEEPSEEK_API_KEY为你自己的DeepSeek API Key
2. 从[本项目的HuggingFace模型页面](https://huggingface.co/wxndong/mygo_bert_demo) 下载模型权重文件，将A和C分别放入对应的文件夹（A -> models/ner_model; C -> models/ner_model_c）
3. `cd backend` && `pip install -r requirements.txt`&& `python app.py`
4. `cd frontend` && `pnpm install` && `pnpm run serve`
ps:如遇到import错误问题，考虑返回根目录，使用带前缀的运行命令（如`python /backend/app.py`，因为作者没有对此进行优化和二次校准）

# 项目演示
## 主页
![主页图片](/assets/homepage.png "System Demo")

## NER模块
上半部分
![NER图片1](/assets/NER-1.png "System Demo")

下半部分
![NER图片2](/assets/NER-2.png "System Demo")

模型热切换
![NER图片3](/assets/NER-3.png "System Demo")

实体解析
![NER图片4](/assets/NER-4.png "System Demo")

## LLM模块
动态路由机制 & 历史对话 & 对话管理
![LLM图片1](/assets/LLM-1.png "System Demo")

## 用户管理模块
注册 & 登录
![USER图片1](/assets/USER-1.png "System Demo")
![USER图片1](/assets/USER-2.png "System Demo")

# 致谢
感谢我的指导教师，感谢EvaHan2025的主办方，感谢审稿人。