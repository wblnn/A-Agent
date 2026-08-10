import asyncio
from openai import AsyncOpenAI

# ==========================================
# 1. 配置你的双模型 (目前都用 koboldcpp 占位)
# ==========================================

# 本地小模型 (日常聊天)
local_client = AsyncOpenAI(
    base_url="http://localhost:5001/v1",
    api_key="not-needed"
)

# 云端大模型 (硬核推理) - 暂时用本地模型占位，以后换成 DeepSeek API
cloud_client = AsyncOpenAI(
    base_url="http://localhost:5001/v1", 
    api_key="not-needed"
)

# ==========================================
# 2. 编写你的智能路由逻辑
# ==========================================
def select_client(prompt: str) -> AsyncOpenAI:
    """根据用户输入，决定使用哪个模型"""
    heavy_keywords = ["写代码", "调试", "bug", "报错", "分析", "算法", "解释"]
    
    if any(keyword in prompt for keyword in heavy_keywords):
        print("🔀 [Router] 检测到硬核任务 -> 路由至 云端大模型 (目前占位)")
        return cloud_client
    else:
        print("🔀 [Router] 日常聊天 -> 路由至 本地小模型 (koboldcpp)")
        return local_client

# ==========================================
# 3. 运行测试
# ==========================================
async def chat_with_agent(user_input: str):
    # 1. 动态选择模型
    client = select_client(user_input)
    
    # 2. 发送请求 (使用最标准的 OpenAI 格式，koboldcpp 完美兼容)
    response = await client.chat.completions.create(
        model="local-model", # 本地调用，名字随意
        messages=[
            {"role": "system", "content": "你是一个有用的AI助手。"},
            {"role": "user", "content": user_input}
        ],
        stream=False # 先测试非流式，确保能拿到完整回复
    )
    
    # 3. 提取并打印回复
    reply = response.choices[0].message.content
    print(f"\n💬 [AI 回复]: {reply}\n")
    print("-" * 30)

async def main():
    print("🚀 启动手写版轻量级 Agent 路由器...\n")
    
    # 测试 1：日常聊天 (应该走本地)
    await chat_with_agent("你好，今天天气怎么样？")
    
    # 测试 2：硬核任务 (应该走云端)
    await chat_with_agent("帮我写一个 Python 的冒泡排序算法。")

if __name__ == "__main__":
    asyncio.run(main())