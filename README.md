# Codex Content Video Skills

面向 Codex 的中文内容视频生产 skill 包：从公开信号、选题和事实边界内的文稿，到 TTS、字幕，以及 HyperFrames 或 Remotion 的本地渲染。

工作流只使用当前对话和当前任务目录中的输入。不读取账号 profile，不创建发布队列，也不会自动推送、上传或通知第三方。

## 安装

在一个项目中安装全部 9 个 skill：

```bash
npx skills add Scitiger-AI/codex-content-video-skills
```

这会安装到当前项目的 `.agents/skills/`。安装完成后，在新的 Codex 对话或下一轮会话中使用。

若需要在本机所有项目中可用，安装到全局 scope：

```bash
npx skills add Scitiger-AI/codex-content-video-skills --global -y
```

## 渲染依赖

选择 Remotion 时，额外安装其官方 skills：

```bash
npx skills add remotion-dev/skills
```

选择 HyperFrames 时，在目标环境执行：

```bash
npx hyperframes skills
```

运行环境需要 Python 3、Node.js 22+、FFmpeg 与 `ffprobe`，以及访问 SciTiger 服务、公开 AI 日报和所选热点来源的网络。

## 配置 SciTiger API Key

TTS 与字幕使用公开 SciTiger 服务。请在 [SciTiger Link](https://link.scitiger.cn/) 获取并管理自己的 API key；每位使用者应使用自己的 key 和对应账户额度。

在本机创建 `~/.codex/scitiger.env`：

```text
SCITIGER_API_KEY=sk-ats-...
```

不要将 key 粘贴到对话、脚本、任务产物或 Git 仓库中。无需配置 `SCITIGER_BASE_URL`，skill 固定调用 `https://link.scitiger.cn`。

## 包含的 Skill

| 阶段 | Skill | 职责 |
| --- | --- | --- |
| 信号 | `public-hot-signals` | 收集通用公开热点信号。 |
| 信号 | `ai-trend-report` | 读取公开 SciTiger AI 日报。 |
| 选题 | `content-topic-selection` | 选择信号源并产出 `topic-brief.json`。 |
| 写稿 | `self-media-script` | 生成有事实边界和视觉节拍的 `script-package.json` 与 `script.md`。 |
| 音频 | `tts-generate-audio` | 默认以语速 `1.0` 生成旁白；用户未指定时使用随包参考音色。 |
| 字幕 | `audio-generate-subtitle` | 从旁白和原稿生成 SRT 与字幕时间段。 |
| 编排 | `content-video-workflow` | 生成 renderer-neutral 的 `video-manifest.json` 并编排全流程。 |
| HyperFrames | `hyperframes-content-video` | 生成可编辑 HyperFrames 工程、本地 MP4 与 QC 报告。 |
| Remotion | `remotion-content-video` | 生成可编辑 Remotion 工程、本地 MP4 与 QC 报告。 |

## 选题路由

- 用户提供明确主题且不要求时效：不抓趋势。
- 非 AI 的当前热点：使用 `public-hot-signals`。
- 用户明确要求 AI 日报：使用 `ai-trend-report`。
- 当前 AI、模型、Agent、提示词或 AI 产品类选题：同时使用两类信号。
- 主题模糊：默认使用公开热点。

仅出现一次 “AI” 字样不会触发 AI 日报。公开热榜和 AI 日报都是注意力信号，不是事实来源；面向观众的事实性说法仍需独立、可核验的来源。

## 使用示例

```text
结合今天公开热榜，做一个 90 秒中文科技知识视频，使用 HyperFrames。
```

```text
基于这个主题写一条 60 秒中文解释视频；使用 Remotion，不需要抓取趋势。
```

```text
为这段现有旁白生成 SRT 字幕，不制作视频。
```

未指定渲染器时，完整工作流默认使用 HyperFrames。HyperFrames 会在高质量渲染前保留本地预览确认步骤；Remotion 与 HyperFrames 的成片都会进行本地 QC。

## 许可证与默认音色

本仓库代码采用 [MIT License](LICENSE)。

`tts-generate-audio/assets/default-reference.mp3` 不受 MIT License 覆盖，适用单独的 [音色授权声明](tts-generate-audio/assets/NOTICE)：允许原样公开再分发，并允许使用该音色生成非商用旁白；禁止商用、模型训练或微调、创建其他可复用音色或变体、修改参考音频、以及重新授权该音频。

因此，商业、赞助、客户、付费或变现内容必须使用使用者自行提供且已获必要授权的 `--reference-audio`，不能使用包内默认音色。

## 安全与分发

- 不要提交 API key、`scitiger.env`、签名媒体 URL、任务产物或本地缓存。
- 保留 [NOTICE](NOTICE) 与音色授权声明；不要将默认参考音色作为 MIT 代码的一部分重新授权。
- 热点源、SciTiger 服务及渲染工具仍受各自服务条款和可用性约束。
- 所有最终产物默认保留本地；发布、上传或通知第三方必须由使用者另行明确授权。
