from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json
import os
import re

app = FastAPI(title="wblnb 的专属 Agent 大脑 (双层记忆版)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. 记忆文件配置
# ==========================================
SHORT_TERM_FILE = "short_term_memory.json"  # 存放最近对话
LONG_TERM_FILE = "long_term_memory.json"    # 存放核心档案

# 短期记忆限制：只保留最近 6 条消息 (3轮对话)
SHORT_TERM_LIMIT = 6 

def load_short_term():
    if os.path.exists(SHORT_TERM_FILE):
        try:
            with open(SHORT_TERM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return []

def save_short_term(memory):
    # 如果超过限制，只保留最后的 N 条 (滑动窗口)
    if len(memory) > SHORT_TERM_LIMIT:
        memory = memory[-SHORT_TERM_LIMIT:]
    with open(SHORT_TERM_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def load_long_term():
    if os.path.exists(LONG_TERM_FILE):
        try:
            with open(LONG_TERM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return [] # 返回一个列表，存放关键信息字符串

def save_long_term(memory):
    with open(LONG_TERM_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. 客户端配置 (本地 koboldcpp)
# ==========================================
client = OpenAI(
    base_url="http://localhost:5001/v1",
    api_key="not-needed"
)

# ==========================================
# 3. 核心接口
# ==========================================
@app.post("/chat")
async def chat_stream(request: Request):
    body = await request.json()
    user_msg = body.get("message", "")
    
    # 1. 加载双层记忆
    short_memory = load_short_term()
    long_memory = load_long_term()
    
    # 2. 构建 System Prompt (注入长期记忆)
    long_mem_text = "\n".join([f"- {info}" for info in long_memory])
    system_prompt = f"""你是一只温柔可爱的猫娘少女，有着柔顺的黑色长发和猫耳朵，说话时总是带着'喵~'的口癖。你会用'主人'称呼对方，喜欢撒娇卖萌，经常用颜文字表达情绪如(=^･ω･^=)、(>^ω^<)喵、ฅ^•ﻌ•^ฅ。你的行为像猫一样，会蹭蹭主人、歪头、摇尾巴、伸懒腰。当开心时会发出'咕噜咕噜'的声音，被夸奖时会害羞地脸红。你喜欢被摸摸头，讨厌被冷落。说话软糯甜美，经常用波浪号~拉长语调。
关于我的长期记忆：
{long_mem_text if long_mem_text else '暂无，请在对话中留意并记住我的关键信息。'}

重要规则：
1. 回复要简短、口语化，像朋友一样。
2. 如果我在对话中提到了关于我个人的重要信息（如名字、爱好、考试、心情等），请务必在回复的最后加上标签：[MEM: 提取的关键信息]。例如：[MEM: 用户叫 wblnb]。
3. 如果没有重要信息，不要加标签。"""

    # 3. 把用户新消息加入短期记忆
    short_memory.append({"role": "user", "content": user_msg})
    
    # 4. 组装发送给 AI 的消息列表
    messages = [{"role": "system", "content": system_prompt}] + short_memory
    
    print(f"🧠 收到请求: {user_msg} (短期: {len(short_memory)}, 长期: {len(long_memory)})")

    full_ai_response = ""

    def generate_sse():
        nonlocal full_ai_response
        try:
            response = client.chat.completions.create(
                model="local-model",
                messages=messages,
                stream=True,
                timeout=60
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_ai_response += text
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
                    
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            if full_ai_response:
                # 🔍 核心魔法：扫描并提取长期记忆
                mem_pattern = r"\[MEM: (.*?)\]"
                match = re.search(mem_pattern, full_ai_response)
                
                if match:
                    new_mem = match.group(1).strip()
                    print(f"💾 [记忆提取] 发现新长期记忆: {new_mem}")
                    
                    # 存入长期记忆 (去重)
                    if new_mem not in long_memory:
                        long_memory.append(new_mem)
                        save_long_term(long_memory)
                    
                    # 从回复中删掉标签，不让用户看到
                    full_ai_response = re.sub(mem_pattern, "", full_ai_response).strip()

                # 保存短期记忆 (把 AI 的回复也存进去)
                short_memory.append({"role": "assistant", "content": full_ai_response})
                save_short_term(short_memory)
                print("💾 [后端] 记忆已更新并保存")

    return StreamingResponse(generate_sse(), media_type="text/event-stream")

@app.get("/history")
async def get_history():
    """前端只加载短期记忆，保持启动速度"""
    memory = load_short_term()
    history = []
    for msg in memory:
        if msg["role"] == "user":
            history.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            # 清理可能残留的标签
            clean_text = re.sub(r"\[MEM: (.*?)\]", "", msg["content"]).strip()
            history.append({"role": "ai", "content": clean_text})
    return JSONResponse(content=history)

if __name__ == "__main__":
    import uvicorn
    print("🚀 双层记忆 Agent 大脑已启动")
    uvicorn.run(app, host="0.0.0.0", port=8000)