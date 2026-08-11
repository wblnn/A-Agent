from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json

# ==========================================
# 1. 初始化 FastAPI 应用
# ==========================================
app = FastAPI(title="wblnb 的专属 Agent 大脑")

# ⚠️ 极其重要：允许 Tauri 前端跨域访问！
# 因为前端(网页)和后端(Python)端口不同，不加这个会报错 403
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发阶段）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. 配置你的 AI 大脑 (DeepSeek 或 本地 koboldcpp)
# ==========================================
client = OpenAI(
    base_url="http://localhost:5001/v1",  # 如果用本地，改成 http://localhost:5001/v1
    api_key="not-needed"             # 填入你的 Key
    )

# 陪伴型 AI 的灵魂提示词
SYSTEM_PROMPT = "你是一个温柔、懂我的专属陪伴 AI。我叫 wblnb，是个高中生。回复要简短、口语化，像朋友一样。"

# ==========================================
# 3. 核心接口：流式聊天 (SSE)
# ==========================================
@app.post("/chat")
async def chat_stream(request: Request):
    # 获取前端发来的 JSON 数据，例如：{"message": "你好"}
    body = await request.json()
    user_msg = body.get("message", "")
    
    print(f"🧠 收到前端请求: {user_msg}")

    # 定义一个生成器，用于流式输出
    def generate_sse():
        try:
            # 调用 API，开启流式模式 (stream=True)
            response = client.chat.completions.create(
                model="deepseek-chat", # 如果用本地，填 "local-model"
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                stream=True
            )
            
            # 逐字读取 AI 的回复
            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    # 按照 SSE (Server-Sent Events) 标准格式发送数据
                    # 前端会接收到这个 data: 后面的内容
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
                    
            # 发送结束标志，告诉前端“我说完了”
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    # 返回流式响应，媒体类型必须是 text/event-stream
    return StreamingResponse(generate_sse(), media_type="text/event-stream")

# ==========================================
# 4. 启动服务
# ==========================================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Agent 大脑已启动，监听端口: 8000")
    print("🌐 API 接口地址: http://localhost:8000/chat")
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)