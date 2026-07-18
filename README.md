# Codex Content Video Skills

面向 Codex 的任务级中文内容视频工作流：从公开信号和选题，到事实边界内的文稿、TTS、字幕，以及 HyperFrames 或 Remotion 渲染。

它不使用账号 profile、发布队列、自动推送或第三方通知。每次运行只使用当前对话和当前任务目录中的输入。

## 安装

```bash
npx skills add Scitiger-AI/codex-content-video-skills
```

使用 Remotion 渲染时，额外安装其官方 skills：

```bash
npx skills add remotion-dev/skills
```

使用 HyperFrames 渲染时，在目标环境执行：

```bash
npx hyperframes skills
```

## 运行环境

- Python 3
- Node.js 22+
- FFmpeg 与 `ffprobe`
- 可访问公开 SciTiger 接口、公开 AI 日报和所选热点来源的网络

TTS 与字幕需要每位使用者自己的 SciTiger API key。创建 `~/.codex/scitiger.env`：

```text
SCITIGER_API_KEY=sk-ats-...
```

不要提交这个文件，也不需要配置 `SCITIGER_BASE_URL`。

## 工作流

1. `public-hot-signals` 收集通用公开热点信号。
2. `ai-trend-report` 读取公开 AI 日报。
3. `content-topic-selection` 按当前任务选择信号源并产出 `topic-brief.json`。
4. `self-media-script` 生成带事实边界和视觉节拍的 `script-package.json` 与 `script.md`。
5. `tts-generate-audio` 以默认语速 `1.0` 生成旁白；未指定音色时使用随包分发的参考音色。
6. `audio-generate-subtitle` 基于旁白和原稿生成 SRT 与字幕时间段。
7. `content-video-workflow` 生成 renderer-neutral 的 `video-manifest.json`，并派发至 HyperFrames 或 Remotion。
8. `hyperframes-content-video` 或 `remotion-content-video` 生成本地工程、MP4 和 QC 报告。

选题路由不因出现一次 “AI” 字样就调用 AI 日报：只有用户明确要求，或主题实质属于当前 AI、模型、Agent、提示词或 AI 产品时才会使用它。公开热榜和 AI 日报均是注意力信号，不是事实来源。

## 使用示例

```text
结合今天公开热榜，做一个 90 秒中文科技知识视频，使用 HyperFrames。
```

```text
基于这个主题写一条 60 秒中文解释视频；使用 Remotion，不需要抓取趋势。
```

## 安全与分发

- 不要提交 API key、`scitiger.env`、签名媒体 URL、任务产物或本地缓存。
- `tts-generate-audio/assets/default-reference.mp3` 仅应在已获得的授权范围内再分发和使用。
- 热点源、SciTiger 服务及渲染工具仍受各自服务条款和可用性约束。
- HyperFrames 在高质量渲染前保留预览确认步骤；所有最终产物保持本地，除非用户另行明确授权发布。
