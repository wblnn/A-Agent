<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'

interface Message {
  role: 'user' | 'ai' | 'system'
  text: string
}
const messages = ref<Message[]>([])
const inputMessage = ref('')
const isThinking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

//  新增：启动时加载历史记忆
onMounted(async () => {
  try {
    const response = await fetch('http://localhost:8000/history')
    const history = await response.json()
    // 将后端返回的历史转换为前端格式
    messages.value = history.map(msg => ({
      role: msg.role === 'assistant' ? 'ai' : msg.role,
      text: msg.content
    }))
    scrollToBottom()
  } catch (error) {
    console.error("加载历史失败:", error)
  }
})

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || isThinking.value) return

  messages.value.push({ role: 'user', text })
  inputMessage.value = ''
  isThinking.value = true
  scrollToBottom()

  const aiMsgIndex = messages.value.push({ role: 'ai', text: '' }) - 1

  try {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    })

    if (!response.body) throw new Error('No response body')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
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
              messages.value[aiMsgIndex].text += parsed.text
              scrollToBottom()
            }
          } catch (e) {}
        }
      }
    }
  } catch (error) {
    messages.value.push({ role: 'ai', text: ` 连接大脑失败：${error}` })
    isThinking.value = false
  }
}
</script>

<template>
  <div class="flex flex-col h-screen bg-gray-900 text-gray-100 font-sans">
    <header class="flex items-center justify-center h-14 bg-gray-800 border-b border-gray-700 shadow-md">
      <h1 class="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
        ✨ wblnb 的专属陪伴 (已连接记忆)
      </h1>
    </header>

    <main ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
      <div v-if="messages.length === 0" class="text-center text-gray-500 mt-20">
        <p>你好呀，wblnb！今天过得怎么样？</p>
      </div>

      <div v-for="(msg, index) in messages" :key="index" class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
        <div class="max-w-[80%] px-4 py-2 rounded-2xl shadow-sm" 
             :class="msg.role === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-gray-700 text-gray-100 rounded-bl-none'">
          <p class="whitespace-pre-wrap">{{ msg.text }}</p>
        </div>
      </div>
      
      <div v-if="isThinking" class="flex justify-start">
        <div class="bg-gray-700 px-4 py-2 rounded-2xl rounded-bl-none flex space-x-1 items-center">
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
        </div>
      </div>
    </main>

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
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #1f2937; }
::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #6b7280; }
</style>