<template>
  <div class="about-container">
    <div class="page-header">
      <router-link to="/home" class="back-home">
        <i class="arrow"></i>
        返回首页
      </router-link>
      <h1>关于本项目</h1>
    </div>
    
    <section class="section">
      <h2>项目概述</h2>
      <p>Cs4aCNER 是一个面向古汉语文本的智能处理平台，集成了命名实体识别（NER）和大语言模型（LLM）问答两大功能模块，旨在解决古汉语在文本理解和命名实体识别等方面的挑战。</p>
    </section>

    <section class="section">
      <h2>核心功能</h2>
      
      <div class="feature-card">
        <h3>NER模块</h3>
        <p>基于古汉语预训练模型的命名实体识别系统，支持多种实体类型：</p>
        <div class="feature-details">
          <div class="entity-types">
            <h4>历史增强模型支持实体类型：</h4>
            <ul>
              <li><span class="entity-tag nr">NR</span> 人名</li>
              <li><span class="entity-tag ns">NS</span> 地名</li>
              <li><span class="entity-tag nb">NB</span> 书名</li>
              <li><span class="entity-tag no">NO</span> 官职名</li>
              <li><span class="entity-tag ng">NG</span> 国家名</li>
              <li><span class="entity-tag t">T</span> 时间</li>
            </ul>
          </div>
          <div class="entity-types">
            <h4>医疗增强模型支持实体类型：</h4>
            <ul>
              <li><span class="entity-tag zd">ZD</span> 中医疾病</li>
              <li><span class="entity-tag zz">ZZ</span> 证候</li>
              <li><span class="entity-tag zf">ZF</span> 中药方剂</li>
              <li><span class="entity-tag zp">ZP</span> 中药饮片</li>
              <li><span class="entity-tag zs">ZS</span> 症状</li>
              <li><span class="entity-tag za">ZA</span> 穴位</li>
            </ul>
          </div>
        </div>
        <div class="feature-highlights">
          <h4>特色功能：</h4>
          <ul>
            <li>大模型增强：通过 DeepSeek 大模型二次矫正，提高实体识别准确率</li>
            <li>模型热更新：支持基础模型的动态切换</li>
            <li>批量处理：支持文件上传和批量处理</li>
            <li>结果导出：支持分析结果的下载和保存</li>
            <li>LLM模块联动：用户可选中识别的实体直接发起提问</li>
          </ul>
        </div>
      </div>

      <div class="feature-card">
        <h3>LLM问答模块</h3>
        <p>基于查询复杂度的动态路由机制，为用户提供智能化的古汉语问答服务。</p>
        <div class="feature-highlights">
          <h4>核心特点：</h4>
          <ul>
            <li>多轮对话：支持上下文相关的连续对话</li>
            <li>动态路由机制：
              <ul>
                <li>DeepSeek-V3 负责复杂度评估</li>
                <li>低复杂度查询：直接调用 DeepSeek-V3 回答</li>
                <li>高复杂度查询：使用三模型协作机制
                  <ul>
                    <li>DeepSeek-V3 提供传统文化视角</li>
                    <li>DeepSeek-V3 提供逻辑分析视角</li>
                    <li>DeepSeek-R1 作为主力模型生成最终回答</li>
                  </ul>
                </li>
              </ul>
            </li>
            <li>会话管理：支持会话的保存、重命名和删除</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>技术架构</h2>
      <div class="tech-stack">
        <div class="tech-group">
          <h3>前端</h3>
          <ul>
            <li>Vue.js</li>
            <li>JavaScript</li>
            <li>HTML/CSS</li>
          </ul>
        </div>
        <div class="tech-group">
          <h3>后端</h3>
          <ul>
            <li>Python</li>
            <li>Flask</li>
            <li>SQLite</li>
          </ul>
        </div>
        <div class="tech-group">
          <h3>核心模型</h3>
          <ul>
            <li>GujiRoBERTa + CRF</li>
            <li>DeepSeek-R1</li>
            <li>DeepSeek-V3</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>未来规划</h2>
      <ul class="future-plans">
        <li>添加单例模式，防止本地反复加载模型</li>
        <li>引入RAG或Agent机制进一步增强问答能力</li>
        <li>实现项目的Docker化部署</li>
        <li>优化前端界面与用户体验</li>
      </ul>
    </section>
  </div>
</template>

<script>
export default {
  name: 'AboutPage'
}
</script>

<style scoped>
.about-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  color: #2c3e50;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  position: relative;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e0e6ed;
}

.back-home {
  position: absolute;
  left: 0;
  top: 0.5rem;
  display: flex;
  align-items: center;
  color: #1a73e8;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background 0.2s;
}

.back-home:hover {
  background: #e8f0fe;
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

.section {
  margin-bottom: 3rem;
  background: #fff;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  transition: transform 0.2s, box-shadow 0.2s;
}

.section:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.1);
}

h1 {
  text-align: center;
  margin-bottom: 1rem;
  color: #1a73e8;
  font-size: 2.2rem;
}

h2 {
  color: #1a73e8;
  border-bottom: 2px solid #eaeaea;
  padding-bottom: 0.5rem;
  margin-bottom: 1.5rem;
  font-size: 1.8rem;
}

.feature-card {
  margin-bottom: 2rem;
  background: #f9f9f9;
  border-radius: 8px;
  padding: 1.5rem;
  border-left: 4px solid #1a73e8;
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.feature-details {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  margin: 1rem 0;
}

.entity-types {
  flex: 1;
  min-width: 250px;
}

.entity-tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  margin-right: 6px;
  font-weight: bold;
  color: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.nr { background-color: #ff6b6b; }
.ns { background-color: #4dabf7; }
.nb { background-color: #9775fa; }
.no { background-color: #ffa94d; }
.ng { background-color: #3bc9db; }
.t { background-color: #20c997; }
.zd { background-color: #f06595; }
.zz { background-color: #748ffc; }
.zf { background-color: #38d9a9; }
.zp { background-color: #f783ac; }
.zs { background-color: #4c6ef5; }
.za { background-color: #40c057; }

.feature-highlights ul, .entity-types ul {
  padding-left: 1.5rem;
}

.feature-highlights li {
  margin-bottom: 0.5rem;
}

.tech-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  justify-content: space-between;
}

.tech-group {
  flex: 1;
  min-width: 200px;
  background: #f5f7fa;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  transition: transform 0.2s;
}

.tech-group:hover {
  transform: translateY(-2px);
}

.tech-group h3 {
  margin-top: 0;
  color: #1a73e8;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e0e6ed;
}

.future-plans {
  padding-left: 1.5rem;
  line-height: 1.8;
}

.future-plans li {
  margin-bottom: 0.75rem;
}

@media (max-width: 768px) {
  .feature-details {
    flex-direction: column;
    gap: 1rem;
  }
  
  .tech-stack {
    flex-direction: column;
    gap: 1rem;
  }
  
  .back-home {
    position: relative;
    display: inline-block;
    margin-bottom: 1rem;
  }
  
  h1 {
    text-align: left;
    margin-top: 1rem;
  }
}
</style> 