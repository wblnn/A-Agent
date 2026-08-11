<script setup lang="ts">
import { ref, nextTick } from 'vue'

// 聊天记录数组
interface Message {
  role: 'user' | 'ai'
  text: string
}
const messages = ref<Message[]>([])
const inputMessage = ref('')
const isThinking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// 核心：发送消息并处理 SSE 流式响应
const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || isThinking.value) return

  // 1. 添加用户消息
  messages.value.push({ role: 'user', text })
  inputMessage.value = ''
  isThinking.value = true
  scrollToBottom()

  // 2. 预先添加一个空的 AI 消息，用于后续"打字机"填充
  const aiMsgIndex = messages.value.push({ role: 'ai', text: '' }) - 1

  try {
    // 3. 发起 POST 请求到你的 Python 后端
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    })

    if (!response.body) throw new Error('No response body')

    // 4. 获取 ReadableStream 读取器 (SSE 的核心)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    // 5. 循环读取数据流
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 将二进制数据解码为字符串
      const chunk = decoder.decode(value, { stream: true })
      
      // 按行分割 (SSE 格式是 data: ...\n\n)
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') {
            isThinking.value = false
            continue
          }
          
          try {
            const parsed = JSON.parse(dataStr)
            if (parsed.text) {
              // 打字机效果：不断追加文字
              messages.value[aiMsgIndex].text += parsed.text
              scrollToBottom()
            }
          } catch (e) {
            // 忽略解析错误 (可能是因为 chunk 截断了 JSON)
          }
        }
      }
    }
  } catch (error) {
    messages.value.push({ role: 'ai', text: `❌ 连接大脑失败：${error}` })
    isThinking.value = false
  }
}
</script>

<template>
  <div class="flex flex-col h-screen bg-gray-900 text-gray-100 font-sans">
    <!-- 顶部标题栏 -->
    <header class="flex items-center justify-center h-14 bg-gray-800 border-b border-gray-700 shadow-md">
      <h1 class="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
        ✨ wblnb 的专属陪伴
      </h1>
    </header>

    <!-- 聊天内容区 -->
    <main ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
      <div v-if="messages.length === 0" class="text-center text-gray-500 mt-20">
        <p>你好呀，wblnb！今天过得怎么样？</p>
      </div>

      <div v-for="(msg, index) in messages" :key="index" class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
        <div class="max-w-[80%] px-4 py-2 rounded-2xl shadow-sm" 
             :class="msg.role === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-gray-700 text-gray-100 rounded-bl-none'">
          <!-- 处理换行符 -->
          <p class="whitespace-pre-wrap">{{ msg.text }}</p>
        </div>
      </div>
      
      <!-- 思考中动画 -->
      <div v-if="isThinking" class="flex justify-start">
        <div class="bg-gray-700 px-4 py-2 rounded-2xl rounded-bl-none flex space-x-1 items-center">
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
        </div>
      </div>
    </main>

    <!-- 底部输入区 -->
    <footer class="p-4 bg-gray-800 border-t border-gray-700">
      <div class="flex space-x-2">
        <input 
          v-model="inputMessage" 
          @keyup.enter="sendMessage"
          placeholder="说点什么吧..." 
          class="flex-1 bg-gray-700 text-white px-4 py-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
        />
        <button 
          @click="sendMessage" 
          :disabled="isThinking || !inputMessage.trim()"
          class="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-2 rounded-xl font-medium transition-colors">
          发送
        </button>
      </div>
    </footer>
  </div>
</template>

<style>
/* 自定义滚动条样式，让它更精致 */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #1f2937; 
}
::-webkit-scrollbar-thumb {
  background: #4b5563; 
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #6b7280; 
}
</style>