<template>
  <div class="chat-container">
    <!-- 会话列表侧边栏 -->
    <div class="session-sidebar" :class="{ 'collapsed': !showSessionDrawer }">
      <div class="drawer-header">
        <h3>历史会话</h3>
        <button @click="toggleSessionDrawer" class="toggle-drawer">
          <i class="collapse-icon"></i>
        </button>
      </div>
      <div class="session-list">
        <div v-if="sessions.length === 0" class="no-sessions">
          暂无历史会话
        </div>
        <div v-for="session in sessions" :key="session.id" 
             :class="['session-item', sessionId === session.id ? 'active' : '']">
          <div class="session-content" @click="switchSession(session.id)">
            <div class="session-title">{{ session.title }}</div>
            <div class="session-date">{{ formatDate(session.last_activity) }}</div>
          </div>
          <div class="session-actions">
            <button @click="showRenameDialog(session)" class="action-btn rename-btn" title="重命名">
              <i class="edit-icon"></i>
            </button>
            <button @click="confirmDeleteSession(session.id)" class="action-btn delete-btn" title="删除">
              <i class="delete-icon"></i>
            </button>
          </div>
        </div>
      </div>
      <div class="drawer-footer">
        <button @click="createNewSession" class="new-session-btn">新建会话</button>
      </div>
    </div>
    
    <!-- 主要聊天区域 -->
    <div class="main-content" :class="{ 'expanded': !showSessionDrawer }">
      <div class="header-bar">
        <div class="header-left">
          <router-link to="/home" class="back-home">
            <i class="arrow"></i>
            返回主页
          </router-link>
        </div>
        <div class="header-center">
          <h2>古汉语助手（多轮对话）</h2>
        </div>
        <div class="header-right"></div>
      </div>
      
      <!-- 动态路由状态指示器 -->
      <div class="status-bar" v-if="routingStatus">
        <div :class="['status-indicator', routingStatus.deepseek_available ? 'active' : 'inactive']">
          <span class="status-dot"></span>
          动态路由: {{ routingStatus.deepseek_available ? '可用' : '不可用' }}
        </div>
        <div class="chat-info">
          <span v-if="currentSessionTitle" class="current-session-name">
            当前会话: {{ currentSessionTitle }}
          </span>
        </div>
      </div>
      
      <div class="chat-content">
        <div class="chat-box" ref="chatBox">
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <span v-if="msg.role === 'user'">{{ msg.content }}</span>
            <div v-else-if="msg.role === 'assistant'" class="markdown-content" v-html="renderMessage(msg.content)"></div>
            <div v-else>{{ msg.content }}</div>
            
            <div v-if="msg.routingInfo" class="routing-info">
              <span class="complexity">复杂度: {{ msg.routingInfo.complexity }}</span>
              <span class="model-used">模型: {{ msg.routingInfo.model_used }}</span>
            </div>
          </div>
          <div v-if="loading" class="message loading">AI：正在思考...</div>
        </div>
        
        <form @submit.prevent="sendMessage" class="input-container">
          <button type="button" @click="toggleSessionDrawer" class="session-btn" title="会话列表">
            <i class="session-icon"></i>
          </button>
          <input v-model="inputText" type="text" placeholder="请输入古汉语相关问题..." autocomplete="off" />
          <button type="submit" :disabled="loading" class="send-btn">
            <i class="send-icon"></i>
          </button>
        </form>
      </div>
      
      <!-- 设置面板 -->
      <div class="settings-panel">
        <button @click="showSettings = !showSettings" class="settings-toggle">
          {{ showSettings ? '隐藏设置' : '显示设置' }}
        </button>
        
        <div v-if="showSettings" class="settings-content">
          <div class="setting-item">
            <label>
              <input type="checkbox" v-model="useDynamicRouting" />
              启用动态路由
            </label>
            <span class="setting-desc">根据问题复杂度选择不同处理模型</span>
          </div>
          
          <div class="setting-item">
            <button @click="clearHistory" class="clear-btn">清空当前会话</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 重命名对话框 -->
    <div v-if="showRename" class="modal-backdrop">
      <div class="modal-dialog">
        <div class="modal-header">
          <h4>重命名会话</h4>
          <button @click="showRename = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <input 
            type="text" 
            v-model="newSessionTitle" 
            placeholder="请输入新标题" 
            class="rename-input"
            @keyup.enter="renameSession"
          />
        </div>
        <div class="modal-footer">
          <button @click="showRename = false" class="cancel-btn">取消</button>
          <button @click="renameSession" class="confirm-btn">确认</button>
        </div>
      </div>
    </div>
    
    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirm" class="modal-backdrop">
      <div class="modal-dialog">
        <div class="modal-header">
          <h4>删除会话</h4>
          <button @click="showDeleteConfirm = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <p>确定要删除此会话吗？此操作不可恢复。</p>
        </div>
        <div class="modal-footer">
          <button @click="showDeleteConfirm = false" class="cancel-btn">取消</button>
          <button @click="deleteSession" class="delete-confirm-btn">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { marked } from 'marked';

export default {
  data() {
    return {
      sessionId: '',
      inputText: '',
      messages: [],
      loading: false,
      showSettings: false,
      useDynamicRouting: true,
      routingStatus: null,
      showSessionDrawer: false,
      sessions: [],
      showRename: false,
      newSessionTitle: '',
      sessionToRename: null,
      showDeleteConfirm: false,
      sessionIdToDelete: null,
    };
  },
  computed: {
    // 获取当前会话的标题
    currentSessionTitle() {
      if (!this.sessionId || !this.sessions.length) return null;
      const currentSession = this.sessions.find(s => s.id === this.sessionId);
      return currentSession ? currentSession.title : null;
    }
  },
  created() {
    // 检查URL参数中是否有会话ID
    const urlParams = new URLSearchParams(window.location.search);
    const sessionIdParam = urlParams.get('sessionId');
    
    if (sessionIdParam) {
      // 如果URL中有会话ID，则加载该会话
      this.sessionId = sessionIdParam;
      this.loadChatHistory();
    } else {
      // 否则创建新会话
      this.createSession();
    }
    
    this.getRoutingStatus();
    this.loadSessions();
  },
  methods: {
    async createSession() {
      try {
        const response = await axios.get('http://localhost:5000/api/session');
        this.sessionId = response.data.session_id;
        
        // 更新URL，但不重新加载页面
        history.pushState(
          { sessionId: this.sessionId },
          '',
          `?sessionId=${this.sessionId}`
        );
        
        // 清空消息列表
        this.messages = [];
      } catch (error) {
        console.error('Session creation failed:', error);
        this.messages.push({ 
          role: 'error', 
          content: '无法创建会话，请检查网络连接' 
        });
      }
    },
    async getRoutingStatus() {
      try {
        const response = await axios.get('http://localhost:5000/api/routing_status');
        this.routingStatus = response.data;
        
        // 如果动态路由不可用，默认禁用
        if (!this.routingStatus.deepseek_available) {
          this.useDynamicRouting = false;
        }
      } catch (error) {
        console.error('Failed to get routing status:', error);
      }
    },
    async sendMessage() {
      const userInput = this.inputText.trim();
      if (!userInput) return;

      // 在前端先添加消息
      this.messages.push({ role: 'user', content: `你：${userInput}` });
      this.inputText = '';
      this.loading = true;
      this.scrollToBottom();

      try {
        const response = await axios.post('http://localhost:5000/api/chat', {
          query: userInput,
          session_id: this.sessionId,
          use_dynamic_routing: this.useDynamicRouting,
        });

        // 构建回复消息，包含路由信息
        const replyMessage = { 
          role: 'assistant', 
          content: `AI：${response.data.reply}` // 保留"AI："前缀
        };
        
        // 如果有路由信息，添加到消息中
        if (response.data.routing_info) {
          replyMessage.routingInfo = {
            complexity: response.data.routing_info.complexity === 'easy' ? '简单' : '复杂',
            model_used: this.getModelDisplayName(response.data.routing_info.model_used)
          };
        }
        
        this.messages.push(replyMessage);
        
        // 发送消息后刷新会话列表
        this.loadSessions();
      } catch (error) {
        this.messages.push({ 
          role: 'error', 
          content: `发生错误：${error.response?.data?.reply || error.message}` 
        });
      } finally {
        this.loading = false;
        this.scrollToBottom();
      }
    },
    getModelDisplayName(modelId) {
      // 将模型ID转换为友好显示名称
      const modelNames = {
        'deepseek-v3': 'DeepSeek V3',
        'deepseek-chat': 'DeepSeek V3',
        'deepseek-r1': 'DeepSeek R1',
        'deepseek-reasoner': 'DeepSeek R1',
        'qwen-max': 'Qwen Max'
      };
      return modelNames[modelId] || modelId;
    },
    scrollToBottom() {
      this.$nextTick(() => {
        if (this.$refs.chatBox) {
          this.$refs.chatBox.scrollTop = this.$refs.chatBox.scrollHeight;
        }
      });
    },
    async clearHistory() {
      try {
        await axios.post('http://localhost:5000/api/clear_history', {
          session_id: this.sessionId
        });
        this.messages = [];
        // 清空历史后刷新会话列表
        this.loadSessions();
      } catch (error) {
        console.error('Failed to clear history:', error);
      }
    },
    // 添加Markdown渲染方法
    renderMessage(content) {
      // 从内容中去除"AI："前缀
      const textToRender = content.replace(/^AI[:：]\s*/, '');
      // 使用marked渲染Markdown
      return marked(textToRender, { breaks: true, gfm: true });
    },
    // 加载聊天历史
    async loadChatHistory() {
      try {
        const response = await axios.get(`http://localhost:5000/api/history?session_id=${this.sessionId}`);
        if (response.data.success) {
          // 转换为前端所需格式
          this.messages = response.data.history.map(msg => {
            const formattedMsg = {
              role: msg.role,
              content: msg.role === 'user' ? `你：${msg.content}` : `AI：${msg.content}`
            };
            
            // 如果有路由信息，添加到消息中
            if (msg.routingInfo) {
              formattedMsg.routingInfo = {
                complexity: msg.routingInfo.complexity === 'easy' ? '简单' : '复杂',
                model_used: this.getModelDisplayName(msg.routingInfo.model_used)
              };
            }
            
            return formattedMsg;
          });
          
          this.scrollToBottom();
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
        this.messages.push({
          role: 'error',
          content: '加载历史记录失败'
        });
      }
    },
    // 加载会话列表
    async loadSessions() {
      try {
        const response = await axios.get('http://localhost:5000/api/sessions');
        if (response.data.success) {
          this.sessions = response.data.sessions;
        }
      } catch (error) {
        console.error('Failed to load sessions:', error);
      }
    },
    // 切换会话
    switchSession(sessionId) {
      // 如果是当前会话，不做任何操作
      if (this.sessionId === sessionId) {
        this.showSessionDrawer = false;
        return;
      }
      
      this.sessionId = sessionId;
      
      // 更新URL
      history.pushState(
        { sessionId },
        '',
        `?sessionId=${sessionId}`
      );
      
      // 加载新会话的历史记录
      this.loadChatHistory();
      
      // 关闭抽屉
      this.showSessionDrawer = false;
    },
    // 切换会话抽屉
    toggleSessionDrawer() {
      this.showSessionDrawer = !this.showSessionDrawer;
    },
    // 创建新会话
    createNewSession() {
      this.createSession();
      this.showSessionDrawer = false;
    },
    // 格式化日期
    formatDate(dateString) {
      const date = new Date(dateString);
      const now = new Date();
      
      // 如果是今天
      if (date.toDateString() === now.toDateString()) {
        return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
      }
      
      // 如果是昨天
      const yesterday = new Date(now);
      yesterday.setDate(now.getDate() - 1);
      if (date.toDateString() === yesterday.toDateString()) {
        return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
      }
      
      // 其他日期
      return `${date.getMonth()+1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    },
    // 显示重命名对话框
    showRenameDialog(session) {
      this.showRename = true;
      this.newSessionTitle = session.title;
      this.sessionToRename = session;
    },
    // 重命名会话
    async renameSession() {
      if (!this.newSessionTitle.trim()) {
        return;
      }
      
      try {
        await axios.post('http://localhost:5000/api/rename_session', {
          session_id: this.sessionToRename.id,
          title: this.newSessionTitle
        });
        this.showRename = false;
        // 重新加载会话列表
        await this.loadSessions();
      } catch (error) {
        console.error('Failed to rename session:', error);
      }
    },
    // 确认删除会话
    confirmDeleteSession(sessionId) {
      this.showDeleteConfirm = true;
      this.sessionIdToDelete = sessionId;
    },
    // 删除会话
    async deleteSession() {
      try {
        await axios.post('http://localhost:5000/api/delete_session', {
          session_id: this.sessionIdToDelete
        });
        this.showDeleteConfirm = false;
        
        // 如果删除的是当前会话，创建新会话
        if (this.sessionIdToDelete === this.sessionId) {
          await this.createSession();
        }
        
        // 重新加载会话列表
        await this.loadSessions();
      } catch (error) {
        console.error('Failed to delete session:', error);
      }
    }
  },
};
</script>

<style scoped>
.chat-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100vh;
  width: 100%;
  display: flex;
  background: #f5f5f5;
  position: relative;
  overflow: hidden;
}

/* 侧边栏样式 */
.session-sidebar {
  width: 280px;
  height: 100%;
  background: white;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, transform 0.3s ease;
  overflow: hidden;
  flex-shrink: 0;
}

.session-sidebar.collapsed {
  width: 0;
  transform: translateX(-100%);
}

.toggle-drawer {
  background: none;
  color: #5f6368;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-icon {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-left: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
}

.session-sidebar.collapsed .collapse-icon {
  transform: rotate(-135deg);
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  transition: padding-left 0.3s ease;
  overflow: hidden;
  max-width: calc(100% - 280px);
}

.main-content.expanded {
  max-width: 100%;
}

.header-bar {
  display: grid;
  grid-template-columns: 1fr 3fr 1fr;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
}

.header-left {
  text-align: left;
}

.header-center {
  text-align: center;
}

.header-right {
  text-align: right;
}

.back-home {
  display: inline-flex;
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

h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1a73e8;
}

.chat-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.chat-box {
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 16px;
  overflow-y: auto;
  margin-bottom: 15px;
  background: #fafafa;
  flex: 1;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}

.message {
  position: relative;
  margin: 12px 0;
  padding: 14px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  animation: fadeIn 0.3s ease;
  max-width: 85%;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.user {
  background: #e3f2fd;
  color: #1a73e8;
  align-self: flex-end;
  margin-left: auto;
  margin-right: 5px;
  border-bottom-right-radius: 4px;
  border-top-right-radius: 12px;
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
}

.assistant {
  background: #e8f5e9;
  color: #2e7d32;
  align-self: flex-start;
  margin-right: auto;
  margin-left: 5px;
  border-bottom-left-radius: 4px;
  border-top-right-radius: 12px;
  border-top-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

.loading {
  color: #5f6368;
  font-style: italic;
  align-self: center;
  background: rgba(0,0,0,0.03);
  padding: 12px 16px;
  border-radius: 20px;
  margin: 10px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading:before {
  content: "";
  width: 16px;
  height: 16px;
  border: 2px solid #5f6368;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spinner 1s linear infinite;
  display: inline-block;
}

@keyframes spinner {
  to {transform: rotate(360deg);}
}

.input-container {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  position: sticky;
  bottom: 0;
  background: #f5f5f5;
  padding: 12px 5px;
  z-index: 10;
  border-top: 1px solid #e0e0e0;
}

input[type='text'] {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #dadce0;
  border-radius: 24px;
  font-size: 16px;
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  transition: all 0.2s;
}

input[type='text']:focus {
  outline: none;
  border-color: #1a73e8;
  box-shadow: 0 1px 5px rgba(26,115,232,0.2);
}

.send-btn {
  border-radius: 50%;
  width: 44px;
  height: 44px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.session-btn {
  background-color: #f1f3f4;
  color: #5f6368;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 设置面板样式 */
.settings-panel {
  margin-top: 10px;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.drawer-header h3 {
  margin: 0;
  font-size: 18px;
  color: #202124;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.no-sessions {
  color: #5f6368;
  text-align: center;
  padding: 24px 16px;
  font-style: italic;
}

.session-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  border-left: 3px solid transparent;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background-color 0.2s;
}

.session-item:hover {
  background-color: #f5f5f5;
}

.session-item.active {
  background-color: #e8f0fe;
  border-left-color: #1a73e8;
}

.session-content {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.session-title {
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-date {
  font-size: 12px;
  color: #5f6368;
}

.drawer-footer {
  padding: 16px;
  border-top: 1px solid #e0e0e0;
}

.new-session-btn {
  width: 100%;
}

/* 移动端响应式调整 */
@media (max-width: 768px) {
  .chat-container {
    flex-direction: column;
  }
  
  .session-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1000;
    transform: translateX(-100%);
  }
  
  .session-sidebar:not(.collapsed) {
    transform: translateX(0);
    width: 100%;
  }
  
  .main-content {
    max-width: 100%;
    padding: 10px;
  }
  
  .header-bar {
    grid-template-columns: 1fr 2fr 1fr;
  }
  
  h2 {
    font-size: 1.2rem;
  }
}

button {
  padding: 10px 16px;
  background: #1a73e8;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s;
}

button:hover {
  background: #1565c0;
}

button:disabled {
  background-color: #dadce0;
  cursor: not-allowed;
  opacity: 0.7;
}

.settings-toggle {
  width: 100%;
  padding: 8px 12px;
  background-color: #f1f3f4;
  color: #5f6368;
  border: 1px solid #dadce0;
}

.clear-btn {
  background-color: #ea4335;
}

.clear-btn:hover {
  background-color: #d93025;
}

.routing-info {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  font-size: 12px;
  justify-content: flex-end;
}

.complexity, .model-used {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.05);
  color: #5f6368;
  font-weight: 500;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  background: #f8f8f8;
  padding: 10px 15px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  font-size: 14px;
}

.status-indicator {
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.active {
  background: #e8f5e9;
  color: #2e7d32;
}

.active .status-dot {
  background: #2e7d32;
}

.inactive {
  background: #ffebee;
  color: #c62828;
}

.inactive .status-dot {
  background: #c62828;
}

.chat-info {
  font-size: 14px;
  color: #5f6368;
}

.current-session-name {
  font-weight: 500;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  vertical-align: middle;
}

.markdown-content {
  line-height: 1.6;
}

.markdown-content h1, 
.markdown-content h2, 
.markdown-content h3 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  color: #202124;
}

.markdown-content h1 {
  font-size: 1.4rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  padding-bottom: 0.3rem;
}

.markdown-content h2 {
  font-size: 1.2rem;
}

.markdown-content h3 {
  font-size: 1.1rem;
}

.markdown-content p {
  margin-bottom: 0.8rem;
}

.markdown-content ul, 
.markdown-content ol {
  padding-left: 1.5rem;
  margin-bottom: 0.8rem;
}

.markdown-content li {
  margin-bottom: 0.3rem;
}

.markdown-content blockquote {
  border-left: 3px solid rgba(0, 0, 0, 0.2);
  padding-left: 0.8rem;
  margin: 0.8rem 0;
  color: #5f6368;
  font-style: italic;
}

.markdown-content pre {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.8rem;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 0.8rem;
}

.markdown-content code {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}

.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1rem;
}

.markdown-content th, 
.markdown-content td {
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 0.4rem;
  text-align: left;
}

.markdown-content th {
  background: rgba(0, 0, 0, 0.05);
}

.markdown-content a {
  color: #1a73e8;
  text-decoration: none;
}

.markdown-content a:hover {
  text-decoration: underline;
}

.markdown-content img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}

.session-icon {
  display: inline-block;
  width: 18px;
  height: 14px;
  border-top: 2px solid #5f6368;
  border-bottom: 2px solid #5f6368;
  position: relative;
}

.session-icon:before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  transform: translateY(-50%);
  width: 100%;
  height: 2px;
  background-color: #5f6368;
}

.send-icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'%3E%3Cpath d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/%3E%3C/svg%3E");
  background-size: cover;
}

/* 模态框样式 */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1500;
}

.modal-dialog {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: zoom-in 0.2s;
}

@keyframes zoom-in {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h4 {
  margin: 0;
  font-size: 18px;
  color: #202124;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #5f6368;
  cursor: pointer;
  padding: 0;
}

.modal-body {
  padding: 16px;
}

.rename-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dadce0;
  border-radius: 4px;
  font-size: 16px;
}

.rename-input:focus {
  outline: none;
  border-color: #1a73e8;
  box-shadow: 0 1px 2px rgba(26, 115, 232, 0.1);
}

.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.cancel-btn {
  background-color: #f1f3f4;
  color: #5f6368;
  border: 1px solid #dadce0;
}

.cancel-btn:hover {
  background-color: #e8eaed;
}

.confirm-btn {
  background-color: #1a73e8;
}

.delete-confirm-btn {
  background-color: #ea4335;
}

.action-btn {
  background: none;
  border: none;
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.session-actions {
  display: flex;
  gap: 4px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.edit-icon, .delete-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  background-size: cover;
}

.edit-icon {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%235f6368'%3E%3Cpath d='M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z'/%3E%3C/svg%3E");
}

.delete-icon {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23ea4335'%3E%3Cpath d='M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z'/%3E%3C/svg%3E");
}
</style>