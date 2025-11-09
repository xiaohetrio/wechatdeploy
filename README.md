# Chat Backend - AI 对话后端

基于 FastAPI + Claude + MiniMax TTS 的对话后端服务。

## 🚀 Render 部署指南

### 1. 准备工作
- ✅ GitHub 账号（xiaohetrio）
- ✅ Render 账号（用 GitHub 登录）
- ✅ Claude API Key
- ✅ MiniMax API Key

### 2. 推送代码到 GitHub

```bash
cd ~/Desktop/chat-backend

# 初始化 Git
git init
git add .
git commit -m "Initial commit: Chat backend for Render deployment"

# 连接到你的 GitHub repo
git remote add origin https://github.com/xiaohetrio/wechatdeploy.git
git branch -M main
git push -u origin main
```

### 3. 在 Render 创建 Web Service

1. 登录 Render Dashboard: https://dashboard.render.com
2. 点击 **New +** → **Web Service**
3. 选择你的 GitHub repo: `xiaohetrio/wechatdeploy`
4. 配置如下：

   ```
   Name: chat-backend
   Region: Oregon (US West)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn replayable_api:app --host 0.0.0.0 --port $PORT
   Plan: Free
   ```

### 4. 设置环境变量（重要！）

在 Render Dashboard → Environment 页面添加：

| Key | Value | 说明 |
|-----|-------|------|
| `MINIMAX_API_KEY` | `eyJhbGci...` | 你的 MiniMax API Key |
| `CLAUDE_API_KEY` | `sk-ant-api03...` | 你的 Claude API Key |
| `VOICE_ID` | `moss_audio_1383...` | 语音 ID（可选，有默认值） |
| `TTS_MODEL` | `speech-02-turbo` | TTS 模型（可选） |
| `MAX_HISTORY_TURNS` | `8` | 记忆轮数（可选） |
| `SYSTEM_PROMPT` | `雷铁流...` | 角色设定（可选） |

⚠️ **重要**：`MINIMAX_API_KEY` 和 `CLAUDE_API_KEY` 必须设置！

### 5. 部署

点击 **Create Web Service**，Render 会自动：
1. 从 GitHub 拉取代码
2. 安装依赖（requirements.txt）
3. 启动服务

等待 5-10 分钟，部署成功后会得到一个 URL，例如：
```
https://chat-backend-xxxx.onrender.com
```

### 6. 测试 API

访问健康检查接口：
```
https://chat-backend-xxxx.onrender.com/
```

应该返回：
```json
{
  "status": "ok",
  "service": "Chat Backend API",
  "version": "1.0"
}
```

## 📡 API 接口

### POST /api/chat
发送消息

**请求：**
```json
{
  "message": "你好",
  "session_id": "optional-session-id"
}
```

**响应：**
```json
{
  "reply": "雷铁流的回复",
  "session_id": "session-id",
  "turn_count": 1
}
```

### POST /api/tts
生成语音

**请求：**
```json
{
  "text": "要转换的文字"
}
```

**响应：**
```json
{
  "audio_url": "/audio/20251109093156.mp3",
  "audio_id": "20251109093156"
}
```

## 🔧 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export MINIMAX_API_KEY="your-key"
export CLAUDE_API_KEY="your-key"

# 启动服务
python replayable_api.py
```

访问 http://localhost:8000

## 📊 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| MAX_HISTORY_TURNS | 8 | 保留最近 8 轮对话（4-8分钟记忆） |
| max_tokens | 300 | 每次回复最多 300 tokens（2-4句话） |
| model | claude-sonnet-4-5-20250929 | Claude Sonnet 4.5 模型 |
| TTS_MODEL | speech-02-turbo | MiniMax Turbo 版本（省40%） |

## 💰 成本预估

- **Claude API**: ~$8.7/月（8轮记忆 + 精简 PROMPT）
- **MiniMax TTS**: 按使用量计费（Turbo 版便宜 40%）
- **Render 托管**: 免费计划

## 🔒 安全提示

- ⚠️ **不要**把 API Key 提交到 GitHub
- ✅ 所有密钥都通过 Render 环境变量配置
- ✅ `.gitignore` 已配置忽略敏感文件

## 📝 后续步骤

1. 部署成功后，记录 Render URL
2. 在前端项目（wechat-site）配置此 URL
3. 部署前端到 GitHub Pages
4. 测试完整流程

---

**部署问题？** 检查 Render Logs 查看错误信息。
