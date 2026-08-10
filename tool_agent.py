import re
import os
import asyncio
import subprocess
from openai import AsyncOpenAI

client = AsyncOpenAI(base_url="http://localhost:5001/v1", api_key="not-needed")

# ==========================================
# 1. 本地工具函数 (保持不变)
# ==========================================
def save_to_file(filename: str, content: str) -> str:
    filepath = os.path.join(r"E:\agent", filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功！文件已保存到 {filepath}"
    except Exception as e: return f"保存失败：{str(e)}"

def read_from_file(filename: str) -> str:
    filepath = os.path.join(r"E:\agent", filename)
    if not os.path.exists(filepath): return f"读取失败：找不到文件 {filename}"
    try:
        with open(filepath, "r", encoding="utf-8") as f: return f.read()
    except Exception as e: return f"读取失败：{str(e)}"

def run_shell_command(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, cwd=r"E:\agent", capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or result.stderr.strip() or "命令执行成功，但没有输出。"
    except Exception as e: return f"执行失败：{str(e)}"

# ==========================================
# 2. 极简系统提示词 (减轻小模型认知负担)
# ==========================================
SYSTEM_PROMPT = """你是一个本地工具执行器。请只输出以下格式之一，不要说任何废话：
1. 保存：[SAVE_FILE:文件名]内容[/SAVE_FILE]
2. 读取：[READ_FILE:文件名]
3. 命令：[RUN_SHELL:命令]
"""

# ==========================================
# 3. 核心：带“历史清洗”的 Agent 循环
# ==========================================
async def run_tool_agent(user_input: str, history: list):
    print(f"👤 用户指令: {user_input}\n")
    
    # 🧹 核心魔法 1：清洗历史！
    # 坚决不把包含 "[" 标签的原始回复，和 "系统提示" 塞进历史，防止小模型学坏
    clean_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        if msg['role'] == 'user' and not msg['content'].startswith('系统提示'):
            clean_history.append(msg)
        elif msg['role'] == 'assistant' and '[' not in msg['content']:
            clean_history.append(msg)
            
    clean_history.append({"role": "user", "content": user_input})
    
    print("🧠 AI 正在思考...")
    response = await client.chat.completions.create(model="local-model", messages=clean_history)
    assistant_reply = response.choices[0].message.content
    print(f"🤖 AI 原始回复:\n{assistant_reply}\n")
    
    tool_result = None
    action_taken = False
    
    # 🧹 核心魔法 2：超级宽容的正则表达式！
    # 无论它输出 [SAVE_FILE:xxx] 还是 [/SAVE_FILE:xxx]，只要有 SAVE_FILE 就能抓到
    save_match = re.search(r"SAVE_FILE[:\s：]*(.*?)\](.*?)\[/SAVE_FILE\]", assistant_reply, re.DOTALL | re.IGNORECASE)
    if not save_match: # 兜底：匹配它写错的 [/SAVE_FILE:xxx]
        save_match = re.search(r"\[/SAVE_FILE[:\s：]*(.*?)\](.*?)", assistant_reply, re.DOTALL | re.IGNORECASE)
        
    if save_match:
        filename = save_match.group(1).strip()
        content = save_match.group(2).strip()
        print(f"🔧 检测到工具调用！准备执行: 保存文件 {filename}")
        tool_result = save_to_file(filename, content)
        action_taken = True
    else:
        read_match = re.search(r"READ_FILE[:\s：]*(.*?)\]", assistant_reply, re.IGNORECASE)
        if read_match:
            filename = read_match.group(1).strip()
            print(f"🔧 检测到工具调用！准备执行: 读取文件 {filename}")
            tool_result = read_from_file(filename)
            action_taken = True
        else:
            shell_match = re.search(r"RUN_SHELL[:\s：]*(.*?)\]", assistant_reply, re.IGNORECASE)
            if shell_match:
                command = shell_match.group(1).strip()
                print(f"🔧 检测到工具调用！准备执行命令: {command}")
                tool_result = run_shell_command(command)
                action_taken = True
            
    if action_taken:
        print(f"✅ 本地工具执行结果:\n{tool_result}\n")
        
        # 把工具结果喂给它，让它总结
        summary_prompt = clean_history + [
            {"role": "assistant", "content": assistant_reply},
            {"role": "user", "content": f"工具执行结果：{tool_result}。请用一句自然语言总结。"}
        ]
        
        final_response = await client.chat.completions.create(model="local-model", messages=summary_prompt)
        final_reply = final_response.choices[0].message.content
        print(f"🎉 AI 最终回复:\n{final_reply}")
        
        # 👇 关键：只把“最终的自然语言回复”存入全局历史，保持历史干净！
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": final_reply})
        
    else:
        print("💡 未检测到工具调用，AI 认为直接回答即可。")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": assistant_reply})

# ==========================================
# 4. 运行测试
# ==========================================
async def main():
    print("🚀 启动具备“历史清洗”能力的本地 Agent...\n")
    print("="*50)
    
    memory = [] # 全局记忆库
    
    await run_tool_agent("帮我保存一个名叫 test.txt 的文件，里面写上 hello world。", memory)
    print("\n" + "="*50 + "\n")
    
    await run_tool_agent("帮我使用命令看看当前目录下现在有哪些文件？", memory)
    print("\n" + "="*50 + "\n")
    
    await run_tool_agent("根据刚才的命令结果，告诉我目录下有几个 txt 文件？", memory)

if __name__ == "__main__":
    asyncio.run(main())