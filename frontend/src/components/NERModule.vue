<template>
  <div id="ner-module" class="container">
    <!-- 导航栏 -->
    <div class="header-bar">
      <router-link to="/home" class="back-home">
        <i class="arrow"></i>
        返回主页
      </router-link>
      <h2>古汉语命名实体识别 (NER)</h2>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-section glass-card">
      <div class="input-header">
        <h3>输入文本</h3>
        <div class="input-actions">
          <span v-if="enableLLM" class="llm-warning">
            <i>* 启用大模型优化可能需要较长处理时间</i>
          </span>
          <div class="button-group">
            <label class="file-upload-button gradio-button">
              <input 
                type="file" 
                @change="handleFileUpload" 
                accept=".txt"
                :disabled="loading || modelSwitching"
                hidden
              >
              <span>上传文件</span>
            </label>
            <button 
              @click="submitText" 
              :disabled="!inputText || loading || modelSwitching"
              class="gradio-button"
            >
              <span v-if="!loading">分析文本</span>
              <div v-else class="loader"></div>
            </button>
          </div>
        </div>
      </div>
      
      <textarea 
        v-model="inputText" 
        placeholder="请输入或粘贴古汉语文本，或上传.txt文件...（注意不要包含空格）"
        class="gradio-textarea"
        rows="10"
      ></textarea>
    </div>

    <!-- 控制区域 -->
    <div class="controls-section glass-card">
      <div class="controls-row">
        <!-- 模型选择 -->
        <div class="model-control">
          <h3>模型选择</h3>
          <div class="model-switcher">
            <label 
              v-for="model in models" 
              :key="model.type"
              class="model-option"
              :class="{ active: currentModelType === model.type, switching: modelSwitching }"
              @click="!modelSwitching && switchModel(model.type)"
            >
              <input 
                type="radio" 
                :value="model.type" 
                :checked="currentModelType === model.type"
                :disabled="modelSwitching"
                hidden
              >
              <span class="model-name">{{ model.name }}</span>
            </label>
          </div>
        </div>
        
        <!-- 实体类型选择 -->
        <div class="entity-control">
          <h3>实体类型选择</h3>
          <div class="tag-container">
            <label 
              v-for="(entity, index) in entityTypes"
              :key="index"
              class="gradio-tag"
              :class="{ active: selectedEntities.includes(entity.code) }"
            >
              <input 
                type="checkbox" 
                v-model="selectedEntities"
                :value="entity.code"
                hidden
              >
              {{ entity.name }}
            </label>
          </div>
        </div>
        
        <!-- 大模型控制 -->
        <div class="llm-control">
          <h3>大模型优化</h3>
          <div class="switch-container">
            <label class="switch">
              <input type="checkbox" v-model="enableLLM">
              <span class="slider round"></span>
            </label>
            <span class="switch-label">{{ enableLLM ? '启用' : '禁用' }}</span>
          </div>
          <div class="llm-info" v-if="enableLLM">
            使用大模型对基础模型结果进行二次优化，可有效提高实体识别准确率
          </div>
        </div>
      </div>
    </div>

    <!-- 输出区域 -->
    <div class="output-section glass-card">
      <div class="output-header">
        <h3>分析结果</h3>
        <div class="output-actions">
          <button 
            v-if="highlightedText.length" 
            @click="showEntityHelpTip" 
            class="entity-help-button gradio-button secondary-button"
          >
            <span>实体解析</span>
          </button>
          <button 
            v-if="highlightedText.length" 
            @click="downloadResult" 
            class="download-button gradio-button"
          >
            <span>下载结果</span>
          </button>
        </div>
      </div>
      <div v-if="error" class="error-message">
        <p>{{ error }}</p>
      </div>
      <div class="highlighted-text gradio-output">
        <template v-if="highlightedText.length">
          <span 
            v-for="(char, index) in highlightedText"
            :key="index"
            :class="[
              char.highlight ? `entity-${char.label}` : '',
              char.source === 'llm' ? 'llm-enhanced' : ''
            ]"
            class="char-box"
            :title="char.highlight ? `${getEntityName(char.label)}${char.source === 'llm' ? ' (大模型修正)' : ''}` : ''"
            @click="char.highlight && showEntityAnalysis(char, index)"
          >
            {{ char.char }}
          </span>
        </template>
        <div v-else class="placeholder">
          <div class="pulse-animation"></div>
          <p>分析结果将在此处显示...</p>
        </div>
      </div>
      
      <div class="legend" v-if="highlightedText.length">
        <div class="legend-title">图例:</div>
        <div class="legend-items">
          <div v-for="(entity, index) in entityLegend" :key="index" class="legend-item">
            <span class="legend-color" :class="`entity-${entity.code}`"></span>
            <span class="legend-name">{{ entity.name }}</span>
          </div>
          <div class="legend-item">
            <span class="legend-color llm-indicator"></span>
            <span class="legend-name">大模型修正</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 实体分析对话框 -->
    <div class="modal-overlay" v-if="showAnalysisModal" @click="closeAnalysisModal">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <h3>实体解析 - {{ currentEntity.text }} <span class="entity-badge" :class="`entity-${currentEntity.type}`">{{ getEntityName(currentEntity.type) }}</span></h3>
          <button class="close-button" @click="closeAnalysisModal">×</button>
        </div>
        <div class="modal-body">
          <div v-if="analysisLoading" class="analysis-loading">
            <div class="loader"></div>
            <p>正在分析实体信息，请稍候...</p>
          </div>
          <div v-else-if="analysisError" class="analysis-error">
            <p>{{ analysisError }}</p>
          </div>
          <div v-else-if="entityAnalysis" class="analysis-content">
            <div class="analysis-text" v-html="formattedAnalysis"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="gradio-button" @click="closeAnalysisModal">关闭</button>
        </div>
      </div>
    </div>

    <!-- 实体解析提示信息弹窗 -->
    <div class="entity-tip-overlay" v-if="showEntityTip" @click="closeEntityTip">
      <div class="entity-tip-container" @click.stop>
        <div class="entity-tip-header">
          <h3>实体解析功能说明</h3>
          <button class="close-button" @click="closeEntityTip">×</button>
        </div>
        <div class="entity-tip-body">
          <div class="tip-icon">💡</div>
          <div class="tip-content">
            <p><strong>实体解析功能使用说明：</strong></p>
            <ul>
              <li>将鼠标悬停在任何彩色标注的实体上，会显示提示信息</li>
              <li>点击任何识别出的实体，系统将调用大模型分析该实体</li>
              <li>分析结果包含实体的含义、背景知识和相关解释</li>
              <li>特别适合学习理解古汉语文本中的专业术语和实体</li>
            </ul>
            <div class="tip-demo">
              <span class="demo-entity entity-NR">鼠标悬停示例</span> ← 将鼠标悬停在彩色标注的实体上，然后点击查看详细解析
            </div>
          </div>
        </div>
        <div class="entity-tip-footer">
          <button class="gradio-button" @click="closeEntityTip">我知道了</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { marked } from "marked";

export default {
  data() {
    return {
      inputText: "",
      loading: false,
      error: null,
      
      // 模型切换相关
      currentModelType: "A", // 默认使用古汉语历史增强模型A
      models: [
        { type: "A", name: "古汉语历史增强模型" },
        { type: "C", name: "古汉语医疗增强模型" }
      ],
      
      // 历史模型A的实体类型
      entityTypesA: [
        { code: "NB", name: "书名" },
        { code: "NR", name: "人名" },
        { code: "NO", name: "官职名" },
        { code: "NG", name: "国家名" },
        { code: "NS", name: "地名" },
        { code: "T", name: "时间" },
        { code: "O", name: "其他" }
      ],
      
      // 医疗模型C的实体类型
      entityTypesC: [
        { code: "ZD", name: "中医疾病" },
        { code: "ZZ", name: "证候" },
        { code: "ZF", name: "中药方剂" },
        { code: "ZP", name: "中药饮片" },
        { code: "ZS", name: "症状" },
        { code: "ZA", name: "穴位" },
        { code: "O", name: "其他" }
      ],
      
      // 当前选中的实体类型
      selectedEntitiesA: ["NB", "NR", "NO", "NG", "NS", "T"],
      selectedEntitiesC: ["ZD", "ZZ", "ZF", "ZP", "ZS", "ZA"],
      
      highlightedText: [],
      enableLLM: true,
      
      // 实体图例
      entityLegendA: [
        { code: "NB", name: "书名" },
        { code: "NR", name: "人名" },
        { code: "NO", name: "官职名" },
        { code: "NG", name: "国家名" },
        { code: "NS", name: "地名" },
        { code: "T", name: "时间" },
        { code: "O", name: "其他" }
      ],
      entityLegendC: [
        { code: "ZD", name: "中医疾病" },
        { code: "ZZ", name: "证候" },
        { code: "ZF", name: "中药方剂" },
        { code: "ZP", name: "中药饮片" },
        { code: "ZS", name: "症状" },
        { code: "ZA", name: "穴位" },
        { code: "O", name: "其他" }
      ],
      
      currentFile: null,
      analysisResult: null,
      modelSwitching: false,  // 模型切换中状态标记
      
      // 实体解析相关
      showAnalysisModal: false,
      currentEntity: {
        text: "",
        type: "",
        index: -1
      },
      entityAnalysis: null,
      analysisLoading: false,
      analysisError: null,
      
      // 添加实体提示相关数据
      showEntityTip: false,
    };
  },
  computed: {
    // 根据当前模型类型返回对应的实体类型
    entityTypes() {
      return this.currentModelType === "C" ? this.entityTypesC : this.entityTypesA;
    },
    
    // 根据当前模型类型返回对应的已选择实体
    selectedEntities: {
      get() {
        return this.currentModelType === "C" ? this.selectedEntitiesC : this.selectedEntitiesA;
      },
      set(value) {
        if (this.currentModelType === "C") {
          this.selectedEntitiesC = value;
        } else {
          this.selectedEntitiesA = value;
        }
      }
    },
    
    // 根据当前模型类型返回对应的实体图例
    entityLegend() {
      return this.currentModelType === "C" ? this.entityLegendC : this.entityLegendA;
    },
    
    // 当前选中模型的名称
    currentModelName() {
      const model = this.models.find(m => m.type === this.currentModelType);
      return model ? model.name : "";
    },
    
    // 修改 formattedAnalysis 方法，使用 marked 解析 Markdown
    formattedAnalysis() {
      if (!this.entityAnalysis) return "";
      // 使用 marked 解析 Markdown，使其安全并渲染为 HTML
      return marked(this.entityAnalysis, { breaks: true, gfm: true });
    }
  },
  methods: {
    async loadModelInfo() {
      try {
        const response = await axios.get("http://localhost:5000/api/ner/models");
        if (response.data && response.data.current_model) {
          this.currentModelType = response.data.current_model;
          
          // 如果API返回了实体类型信息，更新前端
          if (response.data.available_models) {
            for (const model of response.data.available_models) {
              if (model.type === "A" && model.entity_types) {
                this.entityTypesA = model.entity_types.concat([{ code: "O", name: "其他" }]);
                this.entityLegendA = model.entity_types;
              } else if (model.type === "C" && model.entity_types) {
                this.entityTypesC = model.entity_types.concat([{ code: "O", name: "其他" }]);
                this.entityLegendC = model.entity_types;
              }
            }
          }
        }
      } catch (error) {
        console.error("加载模型信息失败:", error);
        // 使用默认配置
      }
    },
    
    async switchModel(modelType) {
      if (this.currentModelType === modelType || this.loading || this.modelSwitching) {
        return;
      }
      
      this.modelSwitching = true;
      this.error = null;
      
      try {
        // 调用后端API切换模型
        const response = await axios.post(
          "http://localhost:5000/api/ner/switch_model",
          { model_type: modelType },
          {
            headers: { "Content-Type": "application/json" }
          }
        );
        
        if (response.data && response.data.success) {
          // 更新当前模型类型
          this.currentModelType = modelType;
          
          // 清空分析结果
          this.highlightedText = [];
          this.analysisResult = null;
          
          console.log(`模型已切换到: ${this.currentModelName}`);
        } else {
          throw new Error(response.data?.error || "模型切换失败");
        }
      } catch (error) {
        console.error("切换模型失败:", error);
        this.error = error.response?.data?.error || error.message || "切换模型失败，请稍后重试";
      } finally {
        this.modelSwitching = false;
      }
    },
    
    async handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      
      if (!file.name.endsWith('.txt')) {
        this.error = '请上传.txt格式的文件';
        return;
      }
      
      this.error = null;
      this.highlightedText = [];
      this.currentFile = file; // 保存文件对象
      
      try {
        // 读取文件内容并显示
        const reader = new FileReader();
        reader.onload = (e) => {
          this.inputText = e.target.result;
        };
        reader.readAsText(file);
        
        // 清空文件输入
        event.target.value = '';
      } catch (error) {
        this.error = '文件读取失败';
        console.error('File reading error:', error);
      }
    },
    
    async submitText() {
      if (!this.inputText) return;
      
      this.loading = true;
      this.error = null;
      this.highlightedText = [];
      
      try {
        // 无论是文件还是直接输入，都使用文本API进行处理
        // 这样可以确保格式一致，避免文件处理模式下的解析问题
        const response = await axios.post(
          "http://localhost:5000/api/ner",
          { 
            text: this.inputText,
            enable_llm: this.enableLLM,
            model_type: this.currentModelType
          },
          {
            headers: {
              "Content-Type": "application/json",
            },
            timeout: this.enableLLM ? 180000 : 30000
          }
        );
        
        if (!response.data || !Array.isArray(response.data)) {
          throw new Error("返回数据格式错误");
        }
        
        // 保存结果数据（用于下载）
        // 无论是否有文件都生成分析结果
        this.analysisResult = this.formatResultForDownload(response.data);
        console.log("分析结果已生成，长度:", this.analysisResult.length);
        
        // 处理预测结果
        const predictions = response.data;
        this.highlightedText = this.formatHighlightedText(predictions);
      } catch (error) {
        console.error("Error submitting text:", error);
        if (error.code === 'ECONNABORTED') {
          this.error = "请求超时，请减少文本长度或关闭大模型优化后重试";
        } else {
          this.error = error.response?.data?.error || error.message || "提交文本分析失败，请稍后重试";
        }
      } finally {
        this.loading = false;
      }
    },
    
    downloadResult() {
      console.log("下载按钮被点击", {
        hasResult: !!this.analysisResult,
        resultLength: this.analysisResult ? this.analysisResult.length : 0,
        hasFile: !!this.currentFile
      });
      
      // 如果没有分析结果，直接返回
      if (!this.analysisResult) {
        console.error("没有可下载的分析结果");
        this.error = "没有可下载的分析结果，请先分析文本";
        return;
      }
      
      try {
        const resultBlob = new Blob([this.analysisResult], { type: 'text/plain;charset=utf-8' });
        const url = window.URL.createObjectURL(resultBlob);
        
        // 生成文件名，即使没有currentFile也能下载
        const filename = this.currentFile 
          ? `NER_${this.currentFile.name.replace('.txt', '')}_result.txt`
          : `NER_analysis_result_${new Date().toISOString().slice(0,10)}.txt`;
        
        console.log("准备下载文件:", filename);
        
        // 方法1：使用a标签下载
        try {
          const link = document.createElement('a');
          link.href = url;
          link.download = filename;
          link.style.display = 'none';
          document.body.appendChild(link);
          link.click();
          console.log("点击下载链接");
          
          // 延迟移除
          setTimeout(() => {
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            console.log("清理下载资源完成");
          }, 100);
        } catch (e) {
          console.error("方法1下载失败，尝试方法2", e);
          
          // 方法2：直接打开新窗口下载
          const newWindow = window.open(url);
          if (!newWindow) {
            console.error("无法打开新窗口，可能被浏览器阻止");
            throw new Error("浏览器阻止了下载窗口，请允许弹出窗口或检查浏览器设置");
          }
          
          // 清理URL
          setTimeout(() => {
            window.URL.revokeObjectURL(url);
            console.log("清理下载资源完成 (方法2)");
          }, 1000);
        }
      } catch (error) {
        console.error("下载过程中出错:", error);
        this.error = "下载文件失败: " + (error.message || "请稍后重试");
      }
    },
    
    formatResultForDownload(predictions) {
      let result = '';
      let currentEntity = null;
      
      for (let i = 0; i < predictions.length; i++) {
        const item = predictions[i];
        const char = item.char;
        
        // 如果当前不在任何实体中
        if (!currentEntity) {
          // 如果遇到实体开始
          if (item.label !== 'O') {
            result += '[' + char;
            currentEntity = item.label;
          } else {
            // 正常添加非实体字符
            result += char;
          }
        } 
        // 如果已经在实体中
        else {
          // 如果实体类型变化或遇到非实体
          if (item.label !== currentEntity) {
            // 关闭当前实体
            result += ']{' + currentEntity + '}';
            
            // 如果新字符是实体的一部分，开始新实体
            if (item.label !== 'O') {
              result += '[' + char;
              currentEntity = item.label;
            } else {
              // 否则只添加字符
              result += char;
              currentEntity = null;
            }
          } else {
            // 实体类型没变，继续添加到当前实体
            result += char;
          }
        }
      }
      
      // 确保最后一个实体被关闭
      if (currentEntity) {
        result += ']{' + currentEntity + '}';
      }
      
      return result;
    },
    formatHighlightedText(predictions) {
      const result = [];
      predictions.forEach((item) => {
        let baseLabel = item.label;
        let prefix = "";
        
        // 处理BIOES标注格式
        if (item.label.includes("-")) {
          [prefix, baseLabel] = item.label.split("-");
        }
        
        // 确保标签是有效的实体类型
        if (baseLabel && this.entityTypes.some(et => et.code === baseLabel)) {
          // 只有当标签不是O，并且是B(开始)、I(中间)、E(结束)或S(单字)时才高亮
          const isValidEntity = prefix === "B" || prefix === "I" || prefix === "E" || prefix === "S";
          const shouldHighlight = this.selectedEntities.includes(baseLabel) && 
                                 baseLabel !== "O" && 
                                 (!item.label.includes("-") || isValidEntity);
          
          result.push({ 
            char: item.char, 
            label: baseLabel, 
            highlight: shouldHighlight,
            source: item.source || "bert"
          });
        } else {
          // 对于无效标签，将其视为非实体
          result.push({
            char: item.char,
            label: "O",
            highlight: false,
            source: "bert"
          });
        }
      });
      return result;
    },
    getEntityName(code) {
      const entity = this.entityLegend.find(e => e.code === code);
      return entity ? entity.name : code;
    },
    
    // 显示实体解析对话框
    showEntityAnalysis(char, index) {
      // 找到实体的完整文本
      const entityText = this.getCompleteEntityText(index);
      if (!entityText) return;
      
      this.currentEntity = {
        text: entityText,
        type: char.label,
        index: index
      };
      
      this.showAnalysisModal = true;
      this.analysisLoading = true;
      this.analysisError = null;
      this.entityAnalysis = null;
      
      // 调用API获取实体解析
      this.getEntityAnalysis(entityText, char.label);
    },
    
    // 关闭实体解析对话框
    closeAnalysisModal() {
      this.showAnalysisModal = false;
    },
    
    // 获取完整实体文本
    getCompleteEntityText(index) {
      // 如果点击的不是实体，返回空
      if (!this.highlightedText[index] || !this.highlightedText[index].highlight) {
        return "";
      }
      
      const targetLabel = this.highlightedText[index].label;
      let startIndex = index;
      let endIndex = index;
      
      // 向前查找实体开始
      while (
        startIndex > 0 && 
        this.highlightedText[startIndex - 1] && 
        this.highlightedText[startIndex - 1].label === targetLabel &&
        this.highlightedText[startIndex - 1].highlight
      ) {
        startIndex--;
      }
      
      // 向后查找实体结束
      while (
        endIndex < this.highlightedText.length - 1 && 
        this.highlightedText[endIndex + 1] && 
        this.highlightedText[endIndex + 1].label === targetLabel &&
        this.highlightedText[endIndex + 1].highlight
      ) {
        endIndex++;
      }
      
      // 提取完整实体文本
      return this.highlightedText.slice(startIndex, endIndex + 1).map(item => item.char).join("");
    },
    
    // 调用API获取实体解析
    async getEntityAnalysis(entityText, entityType) {
      try {
        const response = await axios.post(
          "http://localhost:5000/api/ner/entity_analysis",
          {
            entity_text: entityText,
            entity_type: entityType,
            context_text: this.inputText,
            model_type: this.currentModelType
          },
          {
            headers: { "Content-Type": "application/json" },
            timeout: 60000 // 最多等待60秒
          }
        );
        
        if (response.data && response.data.analysis) {
          this.entityAnalysis = response.data.analysis;
          this.analysisError = null;
        } else {
          throw new Error("获取解析结果失败");
        }
      } catch (error) {
        console.error("实体解析失败:", error);
        this.analysisError = error.response?.data?.error || error.message || "获取实体解析失败，请稍后重试";
        this.entityAnalysis = null;
      } finally {
        this.analysisLoading = false;
      }
    },
    
    // 显示实体帮助提示
    showEntityHelpTip() {
      this.showEntityTip = true;
    },
    
    // 关闭实体帮助提示
    closeEntityTip() {
      this.showEntityTip = false;
    },
  },
  watch: {
    selectedEntities: {
      handler() {
        // 当选择的实体类型变化时，更新高亮显示
        if (this.highlightedText.length > 0) {
          this.highlightedText = this.highlightedText.map(item => {
            return {
              ...item,
              highlight: this.selectedEntities.includes(item.label) && item.label !== "O"
            };
          });
        }
      },
      deep: true
    },
    
    currentModelType() {
      // 当模型类型变化时，清空分析结果
      this.highlightedText = [];
      this.analysisResult = null;
    }
  },
  async mounted() {
    // 组件挂载时加载模型信息
    await this.loadModelInfo();
  }
};
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header-bar {
  position: relative;
  margin-bottom: 2rem;
  text-align: center;
}

.back-home {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  align-items: center;
  color: #1a73e8;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background 0.2s;
}

.back-home:hover {
  background: #f0f6ff;
}

.arrow {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-left: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  margin-right: 6px;
}

.glass-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  transition: transform 0.2s;
}

.glass-card:hover {
  transform: translateY(-2px);
}

.input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.gradio-button {
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
  color: white;
  border: none;
  padding: 0.8rem 1.5rem;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
}

.gradio-button:disabled {
  background: #e0e0e0;
  cursor: not-allowed;
  opacity: 0.7;
}

.gradio-textarea {
  width: 100%;
  min-height: 200px;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  line-height: 1.6;
  transition: border-color 0.3s;
}

.gradio-textarea:focus {
  border-color: #4CAF50;
  outline: none;
}

.controls-row {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
}

.model-control {
  flex: 1;
  min-width: 300px;
  margin-bottom: 1rem;
}

.entity-control {
  flex: 1;
  min-width: 300px;
}

.llm-control {
  flex: 1;
  min-width: 300px;
}

.model-switcher {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}

.model-option {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 0.8rem;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.model-option:hover:not(.active):not(.switching) {
  background: #e8e8e8;
  transform: translateY(-2px);
}

.model-option.active {
  background: #4CAF50;
  color: white;
  border-color: #45a049;
}

.model-option.switching {
  cursor: not-allowed;
  opacity: 0.7;
}

.model-name {
  font-weight: 500;
}

.tag-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
}

.gradio-tag {
  background: #f5f5f5;
  padding: 0.6rem 1.2rem;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.gradio-tag.active {
  background: #4CAF50;
  color: white;
  border-color: #45a049;
}

.switch-container {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 34px;
  margin-right: 10px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 26px;
  width: 26px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: 0.4s;
}

input:checked + .slider {
  background-color: #4CAF50;
}

input:focus + .slider {
  box-shadow: 0 0 1px #4CAF50;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.slider.round {
  border-radius: 34px;
}

.slider.round:before {
  border-radius: 50%;
}

.switch-label {
  font-weight: 500;
}

.llm-info {
  font-size: 0.9rem;
  color: #666;
  margin-top: 0.5rem;
  background: #f8f8f8;
  padding: 0.8rem;
  border-radius: 8px;
  border-left: 3px solid #4CAF50;
}

.highlighted-text {
  line-height: 1.8;
  font-size: 1.1rem;
}

.char-box {
  display: inline-block;
  min-width: 1em;
  text-align: center;
  transition: background 0.3s;
  padding: 0 1px;
  position: relative;
}

.llm-enhanced {
  border-bottom: 2px dashed #4CAF50;
}

/* 历史模型A的实体样式 */
.entity-NB { background: #2196F3; color: white; }
.entity-NR { background: #E91E63; color: white; }
.entity-NO { background: #9C27B0; color: white; }
.entity-NG { background: #FF9800; color: white; }
.entity-NS { background: #4CAF50; color: white; }
.entity-T { background: #607D8B; color: white; }

/* 医疗模型C的实体样式 */
.entity-ZD { background: #673AB7; color: white; } /* 中医疾病 - 深紫色 */
.entity-ZZ { background: #009688; color: white; } /* 证候 - 蓝绿色 */
.entity-ZF { background: #3F51B5; color: white; } /* 中药方剂 - 靛蓝色 */
.entity-ZP { background: #FF5722; color: white; } /* 中药饮片 - 深橙色 */
.entity-ZS { background: #8BC34A; color: white; } /* 症状 - 浅绿色 */
.entity-ZA { background: #795548; color: white; } /* 穴位 - 棕色 */

.entity-O { background: #9E9E9E; color: white; }

.loader {
  width: 20px;
  height: 20px;
  border: 3px solid #fff;
  border-bottom-color: transparent;
  border-radius: 50%;
  animation: rotation 1s linear infinite;
}

@keyframes rotation {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.placeholder {
  text-align: center;
  padding: 2rem;
  color: #757575;
}

.pulse-animation {
  width: 50px;
  height: 50px;
  background: #eee;
  border-radius: 50%;
  margin: 0 auto 1rem;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1); }
  100% { opacity: 0.6; transform: scale(0.9); }
}

.legend {
  margin-top: 1.5rem;
  border-top: 1px solid #eee;
  padding-top: 1rem;
}

.legend-title {
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-right: 1rem;
}

.legend-color {
  width: 20px;
  height: 20px;
  margin-right: 6px;
  border-radius: 4px;
}

.legend-color.entity-NB { background: #2196F3; }
.legend-color.entity-NR { background: #E91E63; }
.legend-color.entity-NO { background: #9C27B0; }
.legend-color.entity-NG { background: #FF9800; }
.legend-color.entity-NS { background: #4CAF50; }
.legend-color.entity-T { background: #607D8B; }

/* 医疗模型C的图例样式 */
.legend-color.entity-ZD { background: #673AB7; }
.legend-color.entity-ZZ { background: #009688; }
.legend-color.entity-ZF { background: #3F51B5; }
.legend-color.entity-ZP { background: #FF5722; }
.legend-color.entity-ZS { background: #8BC34A; }
.legend-color.entity-ZA { background: #795548; }

.legend-color.entity-O { background: #9E9E9E; }

.legend-color.llm-indicator {
  background: transparent;
  border-bottom: 2px dashed #4CAF50;
}

.error-message {
  background-color: #ffebee;
  color: #d32f2f;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  border-left: 4px solid #d32f2f;
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }
  
  .controls-row {
    flex-direction: column;
    gap: 1rem;
  }
  
  .model-control, .entity-control, .llm-control {
    width: 100%;
  }
  
  .header-bar h2 {
    font-size: 1.3rem;
    margin-top: 2rem;
  }
  
  .back-home {
    position: relative;
    display: inline-block;
    margin-bottom: 1rem;
  }
}

.input-section .input-header {
  position: relative;
}

.input-section .input-header .llm-warning {
  position: absolute;
  right: 0;
  bottom: -25px;
  font-size: 0.8rem;
  color: #f57c00;
}

/* 实体解析对话框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
}

.modal-container {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  animation: modal-appear 0.3s ease-out;
}

@keyframes modal-appear {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.entity-badge {
  display: inline-block;
  padding: 0.2rem 0.8rem;
  border-radius: 15px;
  color: white;
  font-size: 0.8rem;
  margin-left: 0.8rem;
}

.close-button {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.close-button:hover {
  background: #f0f0f0;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex-grow: 1;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
}

.analysis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.analysis-loading .loader {
  margin-bottom: 1rem;
  width: 30px;
  height: 30px;
  border-width: 3px;
}

.analysis-error {
  background-color: #ffebee;
  color: #d32f2f;
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid #d32f2f;
}

.analysis-content {
  line-height: 1.6;
}

/* 允许 v-html 渲染的内容共享父组件的样式 */
:deep(.analysis-text) {
  white-space: normal;
}

:deep(.analysis-text h1) {
  font-size: 1.5rem;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.3rem;
}

:deep(.analysis-text h2) {
  font-size: 1.3rem;
  margin-top: 1.3rem;
  margin-bottom: 0.8rem;
}

:deep(.analysis-text h3) {
  font-size: 1.1rem;
  margin-top: 1.1rem;
  margin-bottom: 0.6rem;
}

:deep(.analysis-text ul, .analysis-text ol) {
  padding-left: 1.5rem;
  margin-bottom: 1rem;
}

:deep(.analysis-text li) {
  margin-bottom: 0.5rem;
}

:deep(.analysis-text p) {
  margin-bottom: 1rem;
}

:deep(.analysis-text blockquote) {
  border-left: 4px solid #e0e0e0;
  padding-left: 1rem;
  color: #666;
  margin: 1rem 0;
}

:deep(.analysis-text pre) {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 1rem;
}

:deep(.analysis-text code) {
  background: #f0f0f0;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
}

:deep(.analysis-text table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1rem;
}

:deep(.analysis-text th, .analysis-text td) {
  border: 1px solid #ddd;
  padding: 0.5rem;
}

:deep(.analysis-text th) {
  background: #f5f5f5;
}

/* 实体可点击样式 */
.char-box.entity-NB, .char-box.entity-NR, .char-box.entity-NO, 
.char-box.entity-NG, .char-box.entity-NS, .char-box.entity-T,
.char-box.entity-ZD, .char-box.entity-ZZ, .char-box.entity-ZF,
.char-box.entity-ZP, .char-box.entity-ZS, .char-box.entity-ZA {
  cursor: pointer;
  position: relative;
}

.char-box.entity-NB:hover, .char-box.entity-NR:hover, .char-box.entity-NO:hover, 
.char-box.entity-NG:hover, .char-box.entity-NS:hover, .char-box.entity-T:hover,
.char-box.entity-ZD:hover, .char-box.entity-ZZ:hover, .char-box.entity-ZF:hover,
.char-box.entity-ZP:hover, .char-box.entity-ZS:hover, .char-box.entity-ZA:hover {
  box-shadow: 0 0 0 2px #000, 0 0 0 4px rgba(255, 255, 255, 0.5);
  z-index: 1;
}

.char-box.entity-NB:hover::after, .char-box.entity-NR:hover::after, .char-box.entity-NO:hover::after, 
.char-box.entity-NG:hover::after, .char-box.entity-NS:hover::after, .char-box.entity-T:hover::after,
.char-box.entity-ZD:hover::after, .char-box.entity-ZZ:hover::after, .char-box.entity-ZF:hover::after,
.char-box.entity-ZP:hover::after, .char-box.entity-ZS:hover::after, .char-box.entity-ZA:hover::after {
  content: "点击查看详细解析";
  position: absolute;
  bottom: -30px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 5px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
}

/* 添加按钮和提示样式 */
.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.output-actions {
  display: flex;
  gap: 10px;
}

.secondary-button {
  background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
}

.entity-tip-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
}

.entity-tip-container {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  animation: modal-appear 0.3s ease-out;
}

.entity-tip-header {
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.entity-tip-header h3 {
  margin: 0;
  font-weight: 500;
}

.entity-tip-body {
  padding: 1.5rem;
  display: flex;
  gap: 1rem;
}

.tip-icon {
  font-size: 2rem;
  color: #2196F3;
}

.tip-content {
  flex: 1;
}

.tip-content ul {
  padding-left: 1.5rem;
  margin-bottom: 1.5rem;
}

.tip-content li {
  margin-bottom: 0.5rem;
}

.tip-demo {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.demo-entity {
  padding: 2px 5px;
  border-radius: 3px;
  color: white;
}

.entity-tip-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
}
</style>