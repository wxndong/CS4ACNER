<template>
    <div class="home-container">
      <div class="header-section">
        <h1>古汉语命名实体识别分类系统</h1>
        <p class="subtitle">基于LLM的古汉语文本智能处理平台</p>
      </div>
      
      <nav class="module-nav">
        <router-link 
          v-for="(module, index) in modules"
          :key="module.path"
          :to="{ path: module.path }"
          class="nav-card"
          :class="`card-${index + 1}`"
          exact
        >
          <div class="card-icon" :class="`icon-${index + 1}`"></div>
          <div class="card-content">
            <h3>{{ module.title }}</h3>
            <p>{{ module.description }}</p>
          </div>
          <div class="card-arrow">
            <i class="arrow-icon"></i>
          </div>
        </router-link>
      </nav>
      
      <div class="footer-section">
        <p>© 2025 古汉语智能处理平台，作者：NEFU CS 董文轩</p>
      </div>
      
      <router-view></router-view>
    </div>
  </template>
  
  <script>
  export default {
    data() {
      return {
        modules: [
          {
            title: '命名实体识别',
            path: '/ner',
            description: '古代文献实体标注与分析，支持多种实体类型的识别和导出'
          },
          {
            title: '古汉语智能问答系统',
            path: '/chat',
            description: '支持多轮对话的古汉语智能问答系统，基于动态路由的大模型协作机制'
          },
          {
            title: '关于本项目',
            path: '/about',
            description: '功能介绍、技术架构及使用说明'
          }
        ]
      }
    }
  }
  </script>
  
  <style scoped>
  .home-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background-color: #f5f7fa;
    color: #2c3e50;
  }
  
  .header-section {
    text-align: center;
    margin-bottom: 3rem;
    padding: 2rem 0;
    animation: fadeIn 1s ease-out;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  h1 {
    font-size: 2.5rem;
    color: #1a73e8;
    margin-bottom: 1rem;
  }
  
  .subtitle {
    font-size: 1.2rem;
    color: #5f6368;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .module-nav {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
    margin: 2rem 0;
    flex: 1;
  }
  
  .nav-card {
    padding: 1.8rem;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
    text-decoration: none;
    color: #2c3e50;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
    border-top: 4px solid transparent;
    animation: slideUp 0.5s ease-out forwards;
    animation-delay: calc(0.1s * var(--index, 0));
    opacity: 0;
    transform: translateY(20px);
  }
  
  .card-1 { --index: 1; }
  .card-2 { --index: 2; }
  .card-3 { --index: 3; }
  
  @keyframes slideUp {
    to { opacity: 1; transform: translateY(0); }
  }
  
  .nav-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  }
  
  .card-1 { border-top-color: #4285f4; }
  .card-2 { border-top-color: #34a853; }
  .card-3 { border-top-color: #ea4335; }
  
  .card-icon {
    width: 64px;
    height: 64px;
    margin-bottom: 1rem;
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    opacity: 0.9;
  }
  
  .icon-1 {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%234285f4'%3E%3Cpath d='M4 5h16v2H4V5zm0 5h16v2H4v-2zm0 5h16v2H4v-2z'/%3E%3C/svg%3E");
  }
  
  .icon-2 {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2334a853'%3E%3Cpath d='M21 6h-2v9H6v2c0 .55.45 1 1 1h11l4 4V7c0-.55-.45-1-1-1zm-4 6V3c0-.55-.45-1-1-1H3c-.55 0-1 .45-1 1v14l4-4h10c.55 0 1-.45 1-1z'/%3E%3C/svg%3E");
  }
  
  .icon-3 {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23ea4335'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z'/%3E%3C/svg%3E");
  }
  
  .card-content {
    flex: 1;
  }
  
  .nav-card h3 {
    margin-bottom: 0.75rem;
    color: #1a73e8;
    font-size: 1.4rem;
    font-weight: 600;
  }
  
  .nav-card p {
    line-height: 1.6;
    color: #5f6368;
  }
  
  .card-arrow {
    position: absolute;
    bottom: 1.5rem;
    right: 1.5rem;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s;
  }
  
  .nav-card:hover .card-arrow {
    opacity: 1;
  }
  
  .arrow-icon {
    width: 12px;
    height: 12px;
    border-top: 2px solid #1a73e8;
    border-right: 2px solid #1a73e8;
    transform: rotate(45deg);
  }
  
  .footer-section {
    margin-top: 2rem;
    text-align: center;
    padding: 1rem 0;
    color: #5f6368;
    font-size: 0.9rem;
  }
  
  @media (max-width: 900px) {
    .module-nav {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    
    .card-arrow {
      opacity: 1;
    }
    
    .header-section {
      padding: 1rem 0;
    }
    
    h1 {
      font-size: 2rem;
    }
  }
  </style>