from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

local_model = OpenAIChatModel(
    "local-model",
    provider=OpenAIProvider(base_url="http://localhost:5001/v1", api_key="not-needed")
)

# 使用最基础的 Agent，没有任何框架加持
raw_agent = Agent(local_model)

print("📡 正在使用原生 pydantic-ai 测试 koboldcpp...")
try:
    # 使用同步方法，更直观
    result = raw_agent.run_sync("你好，回复连接成功。")
    print("\n✅ [原生 Agent 回复]:")
    print(result.output)
except Exception as e:
    print(f"\n❌ [原生测试失败]: {e}")
    print("💡 结论：这说明 koboldcpp 的 API 返回格式与 pydantic-ai 存在底层不兼容。")