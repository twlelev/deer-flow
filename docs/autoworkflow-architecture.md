# AutoWorkflow 系统架构文档

> 本文档描述 AutoWorkflow 三仓库协作体系的整体架构、已实现功能和后续计划。

---

## 一、总体架构

```
用户自然语言指令
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              DeerFlow (AI 调度中心)                   │
│  Lead Agent → 理解意图 → 动态编排任务                  │
│                                                     │
│  Tools: MCP Tools / Skills / Subagents              │
│  Port: Nginx:2026 → LangGraph:2024 + Gateway:8001   │
└────────────┬────────────────────┬───────────────────┘
             │ MCP HTTP           │ Skill (本地沙箱)
             ▼                    ▼
┌────────────────────┐   ┌────────────────────────────┐
│ ComfyUI_Webserver  │   │  video-compose Skill       │
│ (AIGC 能力中心)     │   │  (MoviePy 视频合成)         │
│                    │   │  skills/custom/video-compose│
│ Port: 8000         │   └────────────────────────────┘
│ /mcp/ → MCP Server │
│ /api/v1/ → REST    │
└────────┬───────────┘
         │ WebSocket / HTTP
         ▼
┌────────────────────┐
│   ComfyUI Backend  │
│   (GPU 推理引擎)    │
│   Port: 8188       │
└────────────────────┘
```

---

## 二、三仓库说明

| 仓库 | 定位 | 端口 | Git |
|------|------|------|-----|
| `deer-flow` | AI 调度中心，LangGraph Agent，理解用户意图并编排任务 | 2024/8001/3000 | git@github.com:twlelev/deer-flow.git |
| `ComfyUI_Webserver` | AIGC 能力中心，将 ComfyUI workflow 封装为 REST + MCP API | 8000 | git@github.com:twlelev/ComfyUI_Websever.git |
| `MoneyPrinterV2` | 内容创作 CLI，YouTube Shorts / Twitter Bot 等自动化流程 | - | 本地参考 |

---

## 三、DeerFlow → ComfyUI 集成（MCP Server）

### 3.1 架构思路

不预定义创作流程，让 DeerFlow 的 LLM **动态发现和组合** ComfyUI workflow：

```
DeerFlow LLM
  ├── list_workflows()          → 看到所有可用能力
  ├── get_workflow_detail(id)   → 理解参数要求
  ├── upload_file(url)          → 上传参考音频/图片
  ├── run_workflow(id, inputs)  → 执行并等待结果
  └── get_task_result(task_id)  → 查询长任务结果
```

### 3.2 MCP Server 位置

内嵌在 `ComfyUI_Webserver`，挂载于 `/mcp/`：

```
ComfyUI_Websever/app/mcp/
├── __init__.py      # 模块导出
├── server.py        # FastMCP 实例 + 5个 Tool 注册
└── tools.py         # Tool 业务逻辑实现
```

- 传输协议：**MCP Streamable HTTP**
- 与 HTTP API **共用同一任务队列**（GPU 资源统一管理）
- 内部直接调用 `workflow_loader`、`task_queue`、`file_manager`，无 HTTP 自调用

### 3.3 5个 MCP Tools

| Tool | 描述 |
|------|------|
| `list_workflows` | 列出可用 workflow，含自动推导的 input/output 类型 |
| `get_workflow_detail` | 获取完整参数 schema（已过滤内部字段）|
| `run_workflow` | 提交任务并轮询等待完成（对 LLM 透明同步）|
| `upload_file` | 上传文件，支持内部URL/外部URL/base64 三种场景 |
| `get_task_result` | 查询历史任务状态（超时兜底）|

### 3.4 DeerFlow 配置

在 `extensions_config.json` 中添加（零代码改动）：

```json
{
  "mcpServers": {
    "comfyui": {
      "enabled": true,
      "type": "http",
      "url": "http://<comfyui-host>:8000/mcp/",
      "description": "ComfyUI workflow discovery and execution"
    }
  }
}
```

---

## 四、ComfyUI Workflow 能力清单

> 每个 workflow 的 `config.yaml` 均已添加 `meta` 字段，供 LLM 语义推理。

### 音频类

| Workflow ID | 能力 | 输入 | 输出 | 特点 |
|-------------|------|------|------|------|
| `audio/asr` | ASR 语音转文字 | 音频 | 文本 | 自动识别语言，支持中英日韩 |
| `audio/voice_design` | TTS 声音设计 | 文本 + 指令描述 | 音频 | **无需参考音频**，自然语言描述音色 |
| `audio/single_speaker` | TTS 语音克隆 | 音频 + 文本 | 音频 | 需约20秒参考音频 |
| `audio/qwentts_voice_clone_asr` | TTS 克隆（自动提取参考文本） | 音频 + 文本 | 音频 | ASR 自动提取参考文本，更简便 |
| `audio/fish_audio_s2_tts_example_workflow` | TTS 高质量克隆 | 音频 + 文本 | 音频 | 支持情绪标签、多人对话 |
| `audio/removebg_audio` | 人声/伴奏分离 | 音频 | 双音频 | UVR5，输出人声轨和伴奏轨 |

### 图像类

| Workflow ID | 能力 | 输入 | 输出 | 特点 |
|-------------|------|------|------|------|
| `image/z_image_turbo` | 文生图（快速） | 文本 | 图片 | **无需参考图**，支持中文提示词，速度快3-5倍 |
| `image/flux_redux_real_photo_to_anime` | 真实照片转动漫 | 图片 + 文本 | 图片 | Florence2 自动分析图片 |
| `image/infinite_you_workflow` | 人像生成（身份+姿势控制） | 人脸图 + 姿势图 + 文本 | 图片 | 保持人物身份一致性 |
| `image/supir_lightning_example_02` | 图像超分增强 | 图片 | 图片 | 放大至4K，细节重建 |
| `image/qwen_image_layered` | 图层分解 | 图片 | 透明图层 | 分解为多个语义层，适合合成 |

### 视频类

| Workflow ID | 能力 | 输入 | 输出 | 特点 |
|-------------|------|------|------|------|
| `video/video_ltx2_3_i2v` | 图生视频（I2V） | 图片 + 文本 | 视频 | 以参考图为首帧，文本控制运动 |
| `video/video_ltx2_3_t2v` | 文生视频（T2V） | 文本（图片仅定分辨率） | 视频 | **近似无需参考图**，纯文本驱动 |

---

## 五、DeerFlow Skills

### 5.1 video-compose（已实现）

位置：`skills/custom/video-compose/`

**用途**：AI 内容创作流水线的最后一步——将生成的视频片段和 TTS 配音合成最终视频。

```bash
# 基础用法：合并多个视频片段 + 添加音频
python /mnt/skills/custom/video-compose/scripts/compose.py \
  --videos clip1.mp4 clip2.mp4 \
  --audio narration.mp3 \
  --output final.mp4

# 自动调整视频时长匹配音频
python ... --match-audio-duration

# 质量选项：low(500k) / medium(2000k) / high(5000k)
python ... --quality high
```

**依赖**：`moviepy>=1.0.3`，`ffmpeg`（系统安装）

---

## 六、完整创作流水线示例

```
用户: "帮我做一个关于AI的短视频发到YouTube"

DeerFlow Lead Agent:
  1. 生成脚本 + 分镜（LLM 直接生成）
     → 3段分镜，每段约10秒

  2. [MCP] list_workflows(category="video")
     → 选择 video/video_ltx2_3_t2v

  3. [MCP] run_workflow("video/video_ltx2_3_t2v", {prompt: "分镜1描述..."})
     → clip1.mp4（等待约5分钟）

  4. [MCP] run_workflow("video/video_ltx2_3_t2v", {prompt: "分镜2描述..."})
     → clip2.mp4

  5. [MCP] list_workflows(category="audio", keyword="tts")
     → 选择 audio/voice_design（无需参考音频）

  6. [MCP] run_workflow("audio/voice_design", {text: "完整解说词", instruct: "男性，沉稳"})
     → narration.mp3

  7. [Skill] video-compose
     → python compose.py --videos clip1.mp4 clip2.mp4 --audio narration.mp3 --match-audio-duration
     → final_video.mp4

  8. [P3-待实现] platform-publish Skill
     → 上传到 YouTube
```

---

## 七、部署说明

### ComfyUI_Webserver 启动

```bash
# 1. 安装 MCP 依赖（一次性）
pip install "mcp>=1.0.0"

# 2. 启动服务
python main.py

# 启动后确认日志包含：
# MCP 端点: http://0.0.0.0:8000/mcp/
```

### DeerFlow 配置

```bash
# 1. 复制配置文件
cp extensions_config.example.json extensions_config.json

# 2. 编辑 extensions_config.json，将 comfyui 的 enabled 改为 true
# 并更新 url 为实际的 ComfyUI_Webserver 地址

# 3. 重启 DeerFlow（LangGraph server 会自动热重载 MCP 工具）
make dev
```

---

## 八、待实现（Roadmap）

| Phase | 内容 | 状态 |
|-------|------|------|
| P0 | ComfyUI MCP Server（5个 Tools） | ✅ 已完成 |
| P1 | workflow meta 字段语义增强（13个 workflow） | ✅ 已完成 |
| P2 | DeerFlow video-compose Skill（MoviePy） | ✅ 已完成 |
| P3 | DeerFlow platform-publish Skill（Selenium 上传 YouTube/Twitter） | ⏳ 待实现 |
| P4 | workflow meta 字段持续完善（随 workflow 增加） | 🔄 持续进行 |

---

## 九、关键文件索引

```
deer-flow/
├── extensions_config.example.json    # MCP + Skills 配置示例
├── skills/custom/video-compose/      # 视频合成 Skill
│   ├── SKILL.md
│   └── scripts/compose.py
└── docs/autoworkflow-architecture.md  # 本文档

ComfyUI_Websever/
├── app/mcp/                          # MCP Server 实现
│   ├── __init__.py
│   ├── server.py
│   └── tools.py
├── workflows/                        # 所有 workflow（每个含 meta 字段）
│   ├── audio/{asr,tts,clone,...}/config.yaml
│   ├── image/{t2i,enhance,...}/config.yaml
│   └── video/{i2v,t2v}/config.yaml
└── docs/superpowers/specs/           # 设计文档
    └── 2026-03-30-comfyui-mcp-server-design.md
```
