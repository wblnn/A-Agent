import asyncio
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_deep import create_deep_agent

# 1. 配置 koboldcpp
local_model = OpenAIChatModel(
    "local-model",
    provider=OpenAIProvider(
        base_url="http://localhost:5001/v1",
        api_key="not-needed"
    )
)

# 2. 创建 Agent (核心：关闭所有高级功能，做减法！)
dev_agent = create_deep_agent(
    model=local_model,
    web_search=False,           # 关闭联网
    include_subagents=False,    # 关闭子代理
    include_memory=False,       # 关闭长期记忆
    include_skills=False,       # 关闭技能
    include_todo=False,         # 关闭任务规划
    include_plan=False,         # 关闭计划
    include_teams=False,        # 关闭团队
    include_checkpoints=False,  # 关闭检查点
    context_manager=False,      # 关闭上下文管理
    cost_tracking=False,        # 关闭计费追踪
)

# 3. 测试运行
async def test_connection():
    print("📡 极简模式启动，正在连接 koboldcpp...")
    try:
        # 问一个最简单的问题
        result = await dev_agent.run("你好，请回复'连接成功'。")
        print("\n✅ [Agent 回复]:")
        print(result.output)
    except Exception as e:
        print(f"\n❌ [极简模式依然失败]: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())