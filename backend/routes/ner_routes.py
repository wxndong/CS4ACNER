# backend/routes/ner_routes.py
from flask import Blueprint, request, jsonify, send_file
import torch
from transformers import BertTokenizerFast
from bert_crf_model import BERT_CRF
import requests
import json
import logging
import traceback
import os
from werkzeug.utils import secure_filename
from io import BytesIO
import configparser
from pathlib import Path
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置API密钥
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建蓝图
ner_bp = Blueprint("ner", __name__)

# 配置类
class Config:
    """配置管理类"""
    def __init__(self):
        # 默认配置
        # 模型A - 古汉语历史增强模型
        self.model_a_path = "../models/ner_model"
        self.tokenizer_a_path = "../models/ner_model"
        
        # 模型C - 古汉语医疗增强模型
        self.model_c_path = "../models/ner_model_c"
        self.tokenizer_c_path = "../models/ner_model_c"
        
        # 大模型配置
        self.api_endpoint = "https://api.deepseek.com/v1/chat/completions"
        self.api_key = DEEPSEEK_API_KEY
        self.selected_model_name = "deepseek-chat"
        self.request_timeout = 3600  # 秒
        
        # 默认使用模型A
        self.current_model_type = "A"
        
        # 尝试从配置文件加载
        self._load_from_file()
    
    def _load_from_file(self):
        """从配置文件加载配置"""
        try:
            config_path = Path(__file__).parent.parent / "config.ini"
            if config_path.exists():
                config = configparser.ConfigParser()
                config.read(config_path)
                
                if "MODEL" in config:
                    self.model_a_path = config["MODEL"].get("model_a_path", self.model_a_path)
                    self.tokenizer_a_path = config["MODEL"].get("tokenizer_a_path", self.tokenizer_a_path)
                    self.model_c_path = config["MODEL"].get("model_c_path", self.model_c_path)
                    self.tokenizer_c_path = config["MODEL"].get("tokenizer_c_path", self.tokenizer_c_path)
                
                if "API" in config:
                    self.api_endpoint = config["API"].get("endpoint", self.api_endpoint)
                    self.api_key = config["API"].get("api_key", self.api_key)
                    self.selected_model_name = config["API"].get("model_name", self.selected_model_name)
                    self.request_timeout = int(config["API"].get("timeout", str(self.request_timeout)))
                    
                logger.info("配置已从文件加载")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {str(e)}，使用默认配置")
            
    @property
    def model_path(self):
        """根据当前选择的模型类型返回对应的模型路径"""
        return self.model_c_path if self.current_model_type == "C" else self.model_a_path
        
    @property
    def tokenizer_path(self):
        """根据当前选择的模型类型返回对应的分词器路径"""
        return self.tokenizer_c_path if self.current_model_type == "C" else self.tokenizer_a_path

# 加载配置
config = Config()

# 定义标签映射
# 古汉语历史增强模型A的标签映射
id2label_a = {
    0: 'O', 
    1: 'B-NR', 2: 'I-NR', 3: 'E-NR', 4: 'S-NR', 
    5: 'B-NS', 6: 'I-NS', 7: 'E-NS', 8: 'S-NS', 
    9: 'B-NB', 10: 'I-NB', 11: 'E-NB', 12: 'S-NB', 
    13: 'B-NO', 14: 'I-NO', 15: 'E-NO', 16: 'S-NO', 
    17: 'B-NG', 18: 'I-NG', 19: 'E-NG', 20: 'S-NG', 
    21: 'B-T', 22: 'I-T', 23: 'E-T', 24: 'S-T'
}

# 古汉语医疗增强模型C的标签映射
id2label_c = {
    0: 'O',
    1: 'B-ZD', 2: 'I-ZD', 3: 'E-ZD', 4: 'S-ZD',  # 中医疾病
    5: 'B-ZZ', 6: 'I-ZZ', 7: 'E-ZZ', 8: 'S-ZZ',  # 证候
    9: 'B-ZF', 10: 'I-ZF', 11: 'E-ZF', 12: 'S-ZF',  # 中药方剂
    13: 'B-ZP', 14: 'I-ZP', 15: 'E-ZP', 16: 'S-ZP',  # 中药饮片
    17: 'B-ZS', 18: 'I-ZS', 19: 'E-ZS', 20: 'S-ZS',  # 症状
    21: 'B-ZA', 22: 'I-ZA', 23: 'E-ZA', 24: 'S-ZA'   # 穴位
}

# 实体类型集合用于验证
VALID_ENTITY_TYPES_A = {'NR', 'NS', 'NB', 'NO', 'NG', 'T'}
VALID_ENTITY_TYPES_C = {'ZD', 'ZZ', 'ZF', 'ZP', 'ZS', 'ZA'}

# 全局模型和分词器字典
ner_models = {}
ner_tokenizers = {}

# 加载模型和分词器
def load_model(model_type):
    """根据模型类型加载对应的模型和分词器"""
    try:
        if model_type in ner_models and model_type in ner_tokenizers:
            logger.info(f"使用缓存的模型 {model_type}")
            return ner_models[model_type], ner_tokenizers[model_type]
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if model_type == "A":
            model_path = config.model_a_path
            tokenizer_path = config.tokenizer_a_path
        elif model_type == "C":
            model_path = config.model_c_path
            tokenizer_path = config.tokenizer_c_path
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
            
        model = BERT_CRF.from_pretrained(model_path)
        model.to(device)
        tokenizer = BertTokenizerFast.from_pretrained(tokenizer_path)
        
        # 缓存模型和分词器
        ner_models[model_type] = model
        ner_tokenizers[model_type] = tokenizer
        
        logger.info(f"模型 {model_type} 已加载到 {device} 设备")
        return model, tokenizer
        
    except Exception as e:
        logger.error(f"模型 {model_type} 加载失败: {str(e)}")
        raise

# 初始加载默认模型
try:
    model, tokenizer = load_model(config.current_model_type)
except Exception as e:
    logger.error(f"初始模型加载失败: {str(e)}")
    raise

# 大模型集成处理类
class LLMIntegrationHandler:
    """处理大模型API调用以进行实体修正和补充"""
    
    def __init__(self):
        self.api_endpoint = config.api_endpoint
        self.api_key = config.api_key
        self.model_name = config.selected_model_name
        self.timeout = config.request_timeout
        
        # 古汉语历史增强模型A的提示词
        self.entity_prompt_a = """你是古汉语领域专家，请基于以下古汉语文本和预标注实体，结合实体标签，修正实体边界并补充缺失的实体。实体标签为：NR（人名）、NS（地名）、NB（书名）、NO（官职名）、NG（国家名）、T（时间），非实体标签为：O（非实体）。注意识别罕见实体类型，如时间（T）和书名（NB）。
返回结果请严格按照JSON列表格式，每个元素包含'text'（实体文本）、'type'（实体类型）、'start'（起始位置）、'end'（结束位置）、'source':'llm'（来源标识），并请确保返回的实体位置信息与原始文本对齐。
注意：
1. 除了JSON列表外，你不需要输出任何内容，包括```json这种数据。
2. 返回的实体必须与原始文本完全对齐，确保 `start` 和 `end` 的值准确无误。特别注意：`end` 值应该是实体最后一个字符的位置（从0开始计数），例如对于文本"乙酉"，如果它从位置0开始，则 start=0, end=1。
3. 如果现有实体的边界不完整，请修正为完整的实体范围。
4. 补充缺失的古汉语实体，特别是可能遗漏的罕见实体类型，如古汉语时间和古汉语书名。
5. 对于有歧义的实体，请结合文本所在篇章的信息进行判断，选择最合适的实体类型。同一篇古文中的字词含义具有相对一致的表达，这有助于提高实体识别的准确性。
6. 结合实体的上下文信息和实体本身的信息进行综合判断。例如，可以通过上下文判断实体是否为特定领域（如历史、文学）的专有名词。
文本：{text}
现有实体（JSON List of Dict）：{entities}
返回格式：JSON列表
"""

        # 古汉语医疗增强模型C的提示词
        self.entity_prompt_c = """你是古汉语中医领域专家，请基于以下古汉语中医文献和预标注实体，结合实体标签，修正实体边界并补充缺失的实体。实体标签为：ZD（中医疾病）、ZZ（证候）、ZF（中药方剂）、ZP（中药饮片）、ZS（症状）、ZA（穴位），非实体标签为：O（非实体）。请特别注意识别古代中医文献中的特定实体表达。
返回结果请严格按照JSON列表格式，每个元素包含'text'（实体文本）、'type'（实体类型）、'start'（起始位置）、'end'（结束位置）、'source':'llm'（来源标识），并请确保返回的实体位置信息与原始文本对齐。
注意：
1. 除了JSON列表外，你不需要输出任何内容，包括```json这种数据。
2. 返回的实体必须与原始文本完全对齐，确保 `start` 和 `end` 的值准确无误。特别注意：`end` 值应该是实体最后一个字符的位置（从0开始计数），例如对于文本"伤寒"，如果它从位置0开始，则 start=0, end=1。
3. 如果现有实体的边界不完整，请修正为完整的实体范围。
4. 补充缺失的古汉语中医实体，特别注意方剂名称、中药名称和经络穴位等专业术语的识别。
5. 对于有歧义的实体，请结合文本所在篇章的信息进行判断，选择最合适的实体类型。古代中医文献中的术语可能有特定含义。
6. 结合实体的上下文信息和实体本身的信息进行综合判断，特别关注中医特有的表述方式和术语。
文本：{text}
现有实体（JSON List of Dict）：{entities}
返回格式：JSON列表
"""

    def call_llm_api(self, text, entities):
        """发起同步API调用，包含重试和超时处理"""
        max_retries = 3
        timeout = self.timeout
        
        # 准备实体数据
        entities_json = json.dumps(
            [{"text": e["text"], "type": e["type"], "start": e["start"], "end": e["end"]} for e in entities],
            ensure_ascii=False
        )
    
        # 根据当前模型类型选择提示词
        if config.current_model_type == "C":
            prompt = self.entity_prompt_c.format(text=text, entities=entities_json)
        else:
            prompt = self.entity_prompt_a.format(text=text, entities=entities_json)
        
        # 准备请求参数
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        # 发起请求，包含重试逻辑
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                
                # 记录大模型返回的原始响应到日志
                logger.info(f"大模型返回的原始JSON: {response.text}")
                
                return self.parse_api_response(response.json(), text)
            except requests.exceptions.Timeout:
                logger.warning(f"API请求超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"API调用失败: {traceback.format_exc()}")
                if attempt == max_retries - 1:
                    return []
        
        return []

    def parse_api_response(self, response, original_text):
        """解析并验证API响应，确保实体对齐"""
        validated_entities = []
        
        try:
            # 提取实体内容
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                logger.warning("空或无效的API响应")
                return []
                
            # 尝试解析JSON
            try:
                entities = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("JSON解析失败，尝试修复格式")
                content = content.replace("'", '"')
                entities = json.loads(content)
            
            # 验证和修复每个实体
            for ent in entities:
                # 验证实体基本属性
                if not self._validate_entity_basics(ent):
                    continue
                
                # 验证和修正实体位置
                fixed_entity = self._fix_entity_boundaries(ent, original_text)
                if fixed_entity:
                    validated_entities.append(fixed_entity)
                
            logger.info(f"从API响应中解析出 {len(validated_entities)} 个实体")
            return validated_entities
            
        except Exception as e:
            logger.error(f"响应解析失败: {traceback.format_exc()}")
            return []
    
    def _validate_entity_basics(self, entity):
        """验证实体的基本属性"""
        # 检查必要字段
        if not all(k in entity for k in ['text', 'type', 'start', 'end']):
            logger.warning(f"实体缺少必要字段: {entity}")
            return False
            
        # 检查实体文本
        if not entity.get('text'):
            logger.warning(f"实体文本为空: {entity}")
            return False
            
        # 根据当前模型类型选择有效实体类型集合
        valid_entity_types = VALID_ENTITY_TYPES_C if config.current_model_type == "C" else VALID_ENTITY_TYPES_A
        
        # 检查实体类型
        if entity.get('type') not in valid_entity_types:
            logger.warning(f"无效实体类型: {entity.get('type')}")
            return False
            
        return True
        
    def _fix_entity_boundaries(self, entity, text):
        """修正实体边界，确保位置准确"""
        start = entity.get('start', 0)
        end = entity.get('end', 0)
        entity_text = entity.get('text', '')
        
        # 基本范围检查
        if not (0 <= start <= end < len(text)):
            # 尝试在文本中找到实体位置
            new_start = self._find_exact_position(text, entity_text, 0)
            if new_start == -1:
                logger.warning(f"无法找到实体位置: '{entity_text}'")
                return None
                
            # 计算正确的end位置（最后一个字符的位置）
            new_end = new_start + len(entity_text.strip()) - 1
            logger.info(f"已修正实体位置: '{entity_text}' 从 [{start},{end}] 到 [{new_start},{new_end}]")
            start = new_start
            end = new_end
        else:
            # 验证当前位置的文本是否匹配
            actual_text = text[start:end+1]
            if actual_text.strip() != entity_text.strip():
                # 尝试在附近找到精确匹配
                new_start = self._find_exact_position(text, entity_text, start)
                if new_start != -1 and new_start != start:
                    # 计算正确的end位置（最后一个字符的位置）
                    new_end = new_start + len(entity_text.strip()) - 1
                    logger.info(f"调整实体位置: '{entity_text}' 从 [{start},{end}] 到 [{new_start},{new_end}]")
                    start = new_start
                    end = new_end
                    
        # 创建修正后的实体
        return {
            "text": entity_text,
            "type": entity['type'],
            "start": start,
            "end": end,
            "source": "llm"
        }

    def _find_exact_position(self, text, target, start_hint):
        """在文本中找到目标字符串的确切位置，考虑空格和标点符号的差异"""
        if not target:
            return -1
            
        # 清理文本和目标，去除标点和空白字符
        def clean_text(s):
            return re.sub(r'[\s,.，。、；！？:;!?]', '', s)
            
        cleaned_target = clean_text(target)
        
        # 如果清理后目标为空，返回失败
        if not cleaned_target:
            return -1
            
        # 首先尝试在原文中直接查找（精确匹配）
        # 在指定的开始位置附近搜索
        search_range = text[max(0, start_hint - 10):min(len(text), start_hint + len(target) + 10)]
        pos = search_range.find(target)
        if pos != -1:
            return max(0, start_hint - 10) + pos
            
        # 在全文中搜索
        pos = text.find(target)
        if pos != -1:
            return pos
            
        # 如果精确匹配失败，尝试清理后匹配
        # 这种情况下我们需要逐字符扫描文本
        cleaned_text = clean_text(text)
        target_len = len(cleaned_target)
        
        # 从提示位置附近开始搜索
        hint_index = min(max(0, start_hint), len(text) - 1)
        
        # 将原始文本位置映射到清理后的文本位置
        cleaned_index = len(clean_text(text[:hint_index]))
        
        # 在清理后的文本中查找目标
        pos = cleaned_text.find(cleaned_target, cleaned_index)
        if pos == -1:
            # 如果从提示位置开始找不到，尝试从头开始
            pos = cleaned_text.find(cleaned_target)
            
        if pos == -1:
            return -1
            
        # 找到匹配后，我们需要将清理后的位置映射回原始文本位置
        # 计算原始文本中对应的开始位置
        original_pos = 0
        cleaned_pos = 0
        
        for i, char in enumerate(text):
            if cleaned_pos == pos:
                original_pos = i
                break
                
            if not re.match(r'[\s,.，。、；！？:;!?]', char):
                cleaned_pos += 1
                
        return original_pos

# 创建LLM处理器实例
llm_handler = LLMIntegrationHandler()

# 辅助函数
def _convert_tags_to_entities(pred_tags, text):
    """将预测标签转换为实体字典"""
    entities = []
    current_entity = None
    tokens = list(text)
    
    for idx, tag in enumerate(pred_tags):
        # 处理非实体标签
        if tag == 'O':
            if current_entity:
                entities.append(current_entity)
                current_entity = None
            continue
        
        # 解析标签    
        parts = tag.split('-', 1)
        if len(parts) != 2:
            continue
            
        prefix, entity_type = parts
        
        # 处理实体开始标记
        if prefix in ['B', 'S']:
            if current_entity:
                entities.append(current_entity)
            current_entity = {
                "start": idx,
                "end": idx,
                "type": entity_type,
                "text": tokens[idx],
                "source": "bert"
            }
        # 处理实体中间和结束标记
        elif prefix in ['I', 'E'] and current_entity and current_entity['type'] == entity_type:
            current_entity['end'] = idx
            current_entity['text'] += tokens[idx]
        # 处理标签不连续的情况
        else:
            if current_entity:
                entities.append(current_entity)
                current_entity = None
        
        # 处理实体结束标记        
        if prefix in ['E', 'S'] and current_entity:
            entities.append(current_entity)
            current_entity = None
    
    # 处理最后一个可能未闭合的实体        
    if current_entity:
        entities.append(current_entity)
        
    return entities

def _merge_entities(base_ents, llm_ents):
    """合并基础模型和LLM实体，去除重复和重叠"""
    # 无LLM实体时直接返回基础实体
    if not llm_ents:
        return base_ents
        
    merged = []
    llm_ranges = set()
    
    # 收集LLM实体覆盖的位置
    for ent in llm_ents:
        llm_ranges.update(range(ent['start'], ent['end'] + 1))
    
    # 过滤掉与LLM实体重叠的基础实体
    filtered_base = [
        base_ent for base_ent in base_ents
        if not any(pos in llm_ranges for pos in range(base_ent['start'], base_ent['end'] + 1))
    ]
    
    # 合并并按开始位置排序
    merged = sorted(filtered_base + llm_ents, key=lambda x: (x['start'], -x['end']))
    
    # 去除完全重复的实体
    seen = set()
    unique_merged = []
    for ent in merged:
        key = (ent['start'], ent['end'])
        if key not in seen:
            seen.add(key)
            unique_merged.append(ent)
            
    return unique_merged

def format_result_text(token_label_pairs):
    """将实体识别结果格式化为带标记的文本"""
    result_text = ""
    current_entity = None
    
    for i, pair in enumerate(token_label_pairs):
        char = pair["char"]
        label = pair["label"]
        
        # 处理非实体
        if label == "O":
            if current_entity:
                result_text += "]{" + current_entity + "}"
                current_entity = None
            result_text += char
            continue
        
        # 处理实体开始    
        if not current_entity or (i > 0 and token_label_pairs[i-1]["label"] != label):
            if current_entity:
                result_text += "]{" + current_entity + "}"
            result_text += "["
            current_entity = label
        
        # 添加字符    
        result_text += char
    
    # 处理最后一个实体
    if current_entity:
        result_text += "]{" + current_entity + "}"
        
    return result_text

def process_text(text, enable_llm=False, model_type=None):
    """处理文本并返回实体识别结果"""
    # 参数校验
    if not text:
        return None, "输入文本不能为空"
        
    # 如果指定了模型类型，则临时切换配置
    original_model_type = config.current_model_type
    if model_type and model_type in ["A", "C"]:
        config.current_model_type = model_type
        
    try:
        # 根据当前模型类型获取模型和分词器
        current_model, current_tokenizer = load_model(config.current_model_type)
        
        # 获取当前标签映射
        current_id2label = id2label_c if config.current_model_type == "C" else id2label_a
        
        # 准备输入数据
        inputs = current_tokenizer(
            list(text), 
            is_split_into_words=True, 
            max_length=512, 
            truncation=True, 
            padding=True, 
            return_tensors="pt"
        )

        # 移除不需要的字段
        if "token_type_ids" in inputs:
            del inputs["token_type_ids"]

        # 转移到正确设备
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 模型推理
        with torch.no_grad():
            outputs = current_model(**inputs)

        # 获取预测结果
        predictions = outputs["predictions"][0]
        
        # 将预测ID转换为标签（跳过CLS和SEP标记）
        pred_tags = []
        for i, pred in enumerate(predictions):
            if i == 0 or i == len(predictions) - 1:
                continue
            pred_tags.append(current_id2label[pred])

        # 将标签转换为实体
        base_entities = _convert_tags_to_entities(pred_tags, text)
        
        # 根据设置决定是否使用LLM增强
        if enable_llm:
            try:
                # 调用LLM进行实体修正和补充
                llm_entities = llm_handler.call_llm_api(text, base_entities)
                
                # 合并实体
                merged_entities = _merge_entities(base_entities, llm_entities)
                
                # 创建结果
                token_label_pairs = [{"char": char, "label": "O", "source": "bert"} for char in text]
                
                # 更新标签
                for entity in merged_entities:
                    entity_type = entity['type']
                    source = entity.get('source', 'bert')
                    for i in range(entity['start'], entity['end'] + 1):
                        if 0 <= i < len(token_label_pairs):
                            token_label_pairs[i]["label"] = entity_type
                            token_label_pairs[i]["source"] = source
                
            except Exception as e:
                logger.error(f"大模型处理失败: {str(e)}")
                # 失败时退回到使用基础模型结果
                token_label_pairs = [
                    {"char": char, "label": label, "source": "bert"} 
                    for char, label in zip(list(text), pred_tags)
                ]
        else:
            # 不使用LLM，直接返回基础模型结果
            token_label_pairs = [
                {"char": char, "label": label, "source": "bert"} 
                for char, label in zip(list(text), pred_tags)
            ]
        
        # 恢复原来的模型类型
        if model_type:
            config.current_model_type = original_model_type
                           
        return token_label_pairs, None
        
    except Exception as e:
        # 恢复原来的模型类型
        if model_type:
            config.current_model_type = original_model_type
            
        error_msg = f"处理文本时发生错误: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return None, error_msg

# API端点
@ner_bp.route("/ner", methods=["POST"])
def ner():
    """文本实体识别API"""
    try:
        # 解析请求
        data = request.json
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
            
        # 获取参数
        text = data.get("text", "").strip()
        enable_llm = data.get("enable_llm", False)
        model_type = data.get("model_type", config.current_model_type)  # 支持模型热切换
        
        # 验证参数
        if not text:
            return jsonify({"error": "输入文本不能为空"}), 400
            
        if model_type not in ["A", "C"]:
            return jsonify({"error": f"不支持的模型类型: {model_type}"}), 400

        # 处理文本
        token_label_pairs, error = process_text(text, enable_llm, model_type)
        
        # 返回结果
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify(token_label_pairs)
        
    except Exception as e:
        logger.error(f"处理API请求时发生错误: {traceback.format_exc()}")
        return jsonify({"error": f"处理请求时发生错误: {str(e)}"}), 500

@ner_bp.route("/ner/file", methods=["POST"])
def ner_file():
    """文件实体识别API"""
    try:
        # 验证文件存在
        if "file" not in request.files:
            return jsonify({"error": "未找到上传的文件"}), 400
            
        # 获取文件和参数
        file = request.files["file"]
        enable_llm = request.form.get("enable_llm", "false").lower() == "true"
        model_type = request.form.get("model_type", config.current_model_type)  # 支持模型热切换
        
        # 验证文件名
        if file.filename == "":
            return jsonify({"error": "未选择文件"}), 400
            
        # 验证文件扩展名
        if not file.filename.endswith(".txt"):
            return jsonify({"error": "仅支持.txt文件"}), 400
            
        # 验证模型类型
        if model_type not in ["A", "C"]:
            return jsonify({"error": f"不支持的模型类型: {model_type}"}), 400
        
        # 读取并处理文件内容
        content = file.read().decode("utf-8").strip()
        if not content:
            return jsonify({"error": "文件内容为空"}), 400
            
        # 处理文本
        token_label_pairs, error = process_text(content, enable_llm, model_type)
        if error:
            return jsonify({"error": error}), 400
            
        # 格式化结果
        result_text = format_result_text(token_label_pairs)
        
        # 创建输出文件
        output = BytesIO()
        output.write(result_text.encode('utf-8'))
        output.seek(0)
        
        # 生成下载文件名
        filename = secure_filename(file.filename)
        download_name = f"NER_{os.path.splitext(filename)[0]}_result.txt"
        
        # 返回文件
        return send_file(
            output,
            as_attachment=True,
            download_name=download_name,
            mimetype="text/plain"
        )
        
    except Exception as e:
        logger.error(f"文件处理失败: {traceback.format_exc()}")
        return jsonify({"error": f"文件处理失败: {str(e)}"}), 500

# 添加获取模型信息的API
@ner_bp.route("/ner/models", methods=["GET"])
def get_models_info():
    """获取可用的NER模型信息"""
    try:
        models_info = {
            "current_model": config.current_model_type,
            "available_models": [
                {
                    "type": "A",
                    "name": "古汉语历史增强模型",
                    "entity_types": [
                        {"code": "NB", "name": "书名"},
                        {"code": "NR", "name": "人名"},
                        {"code": "NO", "name": "官职名"},
                        {"code": "NG", "name": "国家名"},
                        {"code": "NS", "name": "地名"},
                        {"code": "T", "name": "时间"}
                    ]
                },
                {
                    "type": "C",
                    "name": "古汉语医疗增强模型",
                    "entity_types": [
                        {"code": "ZD", "name": "中医疾病"},
                        {"code": "ZZ", "name": "证候"},
                        {"code": "ZF", "name": "中药方剂"},
                        {"code": "ZP", "name": "中药饮片"},
                        {"code": "ZS", "name": "症状"},
                        {"code": "ZA", "name": "穴位"}
                    ]
                }
            ]
        }
        return jsonify(models_info)
    except Exception as e:
        logger.error(f"获取模型信息失败: {str(e)}")
        return jsonify({"error": "获取模型信息失败"}), 500

# 添加切换默认模型的API
@ner_bp.route("/ner/switch_model", methods=["POST"])
def switch_model():
    """切换默认NER模型"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
            
        model_type = data.get("model_type")
        if not model_type or model_type not in ["A", "C"]:
            return jsonify({"error": f"不支持的模型类型: {model_type}"}), 400
            
        # 更新默认模型类型
        config.current_model_type = model_type
        
        # 预加载模型
        load_model(model_type)
        
        return jsonify({
            "success": True,
            "message": f"已切换到 {model_type} 模型",
            "current_model": model_type
        })
    except Exception as e:
        logger.error(f"切换模型失败: {str(e)}")
        return jsonify({"error": f"切换模型失败: {str(e)}"}), 500

# 添加实体分析API
@ner_bp.route("/ner/entity_analysis", methods=["POST"])
def entity_analysis():
    """实体解析API，调用大模型解释选中的实体"""
    try:
        # 解析请求
        data = request.json
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
            
        # 获取参数
        entity_text = data.get("entity_text")
        entity_type = data.get("entity_type")
        context_text = data.get("context_text")
        model_type = data.get("model_type", config.current_model_type)
        
        # 验证参数
        if not entity_text:
            return jsonify({"error": "实体文本不能为空"}), 400
        if not entity_type:
            return jsonify({"error": "实体类型不能为空"}), 400
        if not context_text:
            return jsonify({"error": "上下文文本不能为空"}), 400
            
        # 验证模型类型
        if model_type not in ["A", "C"]:
            return jsonify({"error": f"不支持的模型类型: {model_type}"}), 400
            
        # 根据模型类型选择提示词模板
        if model_type == "A":
            # 历史模型的提示词
            prompt_template = """你是古汉语领域专家，请解释以下古汉语文本中标注的实体。
文本上下文：{context_text}
实体：{entity_text}
实体类型：{entity_type_desc}

请根据实体类型提供详细解释，包括：
1. 该实体在古汉语中的含义、来源和背景知识
2. 在文本中的具体作用和意义
3. 相关历史背景信息
4. 如有必要，提供现代解释或对应概念

请以学术严谨的态度回答，如果信息不足或有歧义，请明确指出。回答需要全面但简洁，使用通俗易懂的语言。"""
        else:
            # 医疗模型的提示词
            prompt_template = """你是古代中医文献专家，请解释以下古代中医文本中标注的实体。
文本上下文：{context_text}
实体：{entity_text}
实体类型：{entity_type_desc}

请根据实体类型提供详细解释，包括：
1. 该实体在中医学中的含义、功效和应用
2. 在文本中的具体医学意义
3. 相关中医理论背景
4. 如有可能，提供现代医学对应的解释

请以专业严谨的态度回答，如果信息不足或有歧义，请明确指出。回答需要专业且易懂，方便理解古代中医知识。"""
            
        # 获取实体类型中文描述
        entity_type_desc = ""
        if model_type == "A":
            entity_mappings = {
                "NR": "人名", "NS": "地名", "NB": "书名", 
                "NO": "官职名", "NG": "国家名", "T": "时间"
            }
            entity_type_desc = entity_mappings.get(entity_type, entity_type)
        else:
            entity_mappings = {
                "ZD": "中医疾病", "ZZ": "证候", "ZF": "中药方剂",
                "ZP": "中药饮片", "ZS": "症状", "ZA": "穴位"
            }
            entity_type_desc = entity_mappings.get(entity_type, entity_type)
            
        # 填充提示词模板
        prompt = prompt_template.format(
            context_text=context_text,
            entity_text=entity_text,
            entity_type_desc=entity_type_desc
        )
        
        # 调用大模型API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}"
        }
        
        payload = {
            "model": config.selected_model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        response = requests.post(
            config.api_endpoint,
            headers=headers,
            json=payload,
            timeout=config.request_timeout
        )
        
        response.raise_for_status()
        
        # 解析API响应
        content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if not content:
            return jsonify({"error": "大模型返回内容为空"}), 500
            
        return jsonify({
            "analysis": content,
            "entity_text": entity_text,
            "entity_type": entity_type,
            "entity_type_desc": entity_type_desc
        })
        
    except requests.exceptions.Timeout:
        return jsonify({"error": "大模型API请求超时"}), 504
    except Exception as e:
        logger.error(f"实体分析失败: {traceback.format_exc()}")
        return jsonify({"error": f"实体分析失败: {str(e)}"}), 500
