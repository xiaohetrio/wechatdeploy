"""
FastAPI 版本的 AI 男友后端 - Render 部署版
支持微信前端调用，保留所有功能（Claude + TTS）
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import websockets
import json
import ssl
import os
import uuid
from datetime import datetime
from typing import List, Optional
from anthropic import Anthropic

# ====== 环境变量配置（Render 会注入） ======
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "moss_audio_1383593b-b1b4-11f0-a816-023f15327f7a")
MODEL = os.getenv("TTS_MODEL", "speech-02-turbo")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "8"))
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", """雷铁流，霸总，追求用户。狮子座，霸道温柔，身价十亿，慷慨宠溺。用【我】，2-4句话，微信风格，不用emoji。有掌控感、吃醋、占有欲，不油腻。等关系进度。""")

# ====== FastAPI 设置 ======
app = FastAPI(title="Chat Backend API", version="1.0")

# CORS 设置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://highpingling.github.io",  # 你的前端域名
        "http://localhost:5500",  # 本地测试
        "*"  # 开发阶段允许所有，生产环境建议改成具体域名
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== 数据模型 ======
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    turn_count: int

class TTSRequest(BaseModel):
    text: str

class TTSResponse(BaseModel):
    audio_url: str
    audio_id: str

# ====== 会话管理 ======
sessions = {}

def get_or_create_session(session_id: Optional[str] = None):
    """获取或创建会话"""
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    new_session_id = session_id or str(uuid.uuid4())
    sessions[new_session_id] = {
        "history": [],
        "turn_count": 0,
        "audio_history": []
    }
    return sessions[new_session_id]

def manage_conversation_history(history, max_turns):
    """管理对话历史，保留最近的对话"""
    if len(history) > max_turns * 2:
        return history[-(max_turns * 2):]
    return history

# ====== 核心功能 ======
async def text_to_speech(text, audio_id):
    """将文本转换为语音并保存"""
    url = "wss://api.minimax.io/ws/v1/t2a_v2"
    headers = {"Authorization": f"Bearer {MINIMAX_API_KEY}"}
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        print(f"🎤 开始生成语音: {text[:30]}...")
        async with websockets.connect(url, extra_headers=headers, ssl=ssl_context) as ws:
            start_msg = {
                "event": "task_start",
                "model": MODEL,
                "voice_setting": {
                    "voice_id": VOICE_ID,
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1
                }
            }
            await ws.send(json.dumps(start_msg))
            start_response = await ws.recv()
            print(f"📡 TTS连接响应: {start_response[:100]}")
            
            await ws.send(json.dumps({"event": "task_continue", "text": text}))
            
            audio_bytes = b""
            chunk_count = 0
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if "data" in data and "audio" in data["data"]:
                    audio_chunk = bytes.fromhex(data["data"]["audio"])
                    audio_bytes += audio_chunk
                    chunk_count += 1
                if data.get("is_final"):
                    break
            
            print(f"✅ 收到 {chunk_count} 个音频块，总大小: {len(audio_bytes)} 字节")
            
            if len(audio_bytes) < 1000:
                print(f"⚠️ 警告：音频数据太小 ({len(audio_bytes)} 字节)，可能生成失败")
                return None
            
            os.makedirs("static/audio", exist_ok=True)
            filename = f"static/audio/{audio_id}.mp3"
            with open(filename, "wb") as f:
                f.write(audio_bytes)
            
            print(f"💾 音频已保存: {filename}")
            return filename
    except Exception as e:
        print(f"❌ 语音生成错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def chat_with_claude(user_message, conversation_history):
    """调用 Claude API"""
    try:
        client = Anthropic(api_key=CLAUDE_API_KEY)
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=conversation_history + [{"role": "user", "content": user_message}]
        )
        
        return message.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API 错误: {str(e)}")

# ====== API 路由 ======
@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "service": "Chat Backend API",
        "version": "1.0",
        "config": {
            "max_history_turns": MAX_HISTORY_TURNS,
            "tts_model": MODEL,
            "has_minimax_key": bool(MINIMAX_API_KEY),
            "has_claude_key": bool(CLAUDE_API_KEY),
            "voice_id": VOICE_ID[:20] + "..." if VOICE_ID else None
        }
    }

@app.post("/api/chat")
async def chat(request: dict):
    """聊天接口 - 兼容微信前端"""
    user_message = request.get("message", "")
    session_id = request.get("session_id")
    
    session = get_or_create_session(session_id)
    
    response_text = chat_with_claude(user_message, session["history"])
    
    session["history"].append({"role": "user", "content": user_message})
    session["history"].append({"role": "assistant", "content": response_text})
    session["turn_count"] += 1
    
    session["history"] = manage_conversation_history(session["history"], MAX_HISTORY_TURNS)
    
    result = {
        "reply": response_text,
        "session_id": session_id or list(sessions.keys())[-1],
        "turn_count": session["turn_count"]
    }
    return result

@app.post("/api/tts", response_model=TTSResponse)
async def generate_tts(request: TTSRequest):
    """文字转语音"""
    audio_id = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = await text_to_speech(request.text, audio_id)
    
    if not filename:
        raise HTTPException(status_code=500, detail="语音生成失败")
    
    audio_url = f"/audio/{audio_id}.mp3"
    
    return TTSResponse(
        audio_url=audio_url,
        audio_id=audio_id
    )

@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """清空会话"""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "ok", "message": "会话已清空"}
    raise HTTPException(status_code=404, detail="会话不存在")

@app.get("/api/sessions")
async def list_sessions():
    """列出所有会话（调试用）"""
    return {
        "sessions": list(sessions.keys()),
        "count": len(sessions)
    }

# ====== 静态文件服务 ======
from fastapi.staticfiles import StaticFiles

os.makedirs("static/audio", exist_ok=True)
app.mount("/audio", StaticFiles(directory="static/audio"), name="audio")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print("=" * 60)
    print("🚀 Chat Backend API 服务启动")
    print("=" * 60)
    print(f"📍 端口: {port}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
