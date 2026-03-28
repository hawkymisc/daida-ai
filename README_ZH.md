[English](./README.md) | [日本語](./README_JA.md) | [简体中文](./README_ZH.md) | [한국어](./README_KO.md)

# 救场AI

自动生成演讲材料的 Claude Code 插件 — 让AI替你上场。

> **daida-ai**（源自日语 *daida* 代打 — 替补击球手）：就像救场英雄在关键时刻挺身而出，这个插件替你搞定整场演讲。

## 功能概述

1. 输入演讲主题，自动生成 Markdown 格式的演讲大纲
2. 根据大纲创建幻灯片
   - 以 PowerPoint 格式生成
   - 使用预设计的幻灯片模板（深色科技风、暖色休闲风、正式商务风）
   - 基于专业布局创建幻灯片，而非空白页面
   - 标题和正文设置在大纲可访问的占位符中
3. 在幻灯片备注中写入演讲稿（台词）
   - 支持多种说话风格：休闲、主题演讲、正式、幽默
4. 将演讲稿合成为语音
   - 发音词典自动纠正常见的 TTS 误读
   - 可导出 TTS 脚本进行手动编辑
5. 将合成语音嵌入幻灯片
6. 配置幻灯片自动播放

## 支持格式

PPTX 和 ODP（开放文档演示格式）

## 安装

### 前提条件

- 已安装 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.11 以上

### 第 1 步：添加市场源

在 Claude Code 中执行：

```
/plugin marketplace add hawkymisc/daida-ai
```

### 第 2 步：安装插件

```
/plugin install daida-ai@hawkymisc-daida-ai
```

### 第 3 步：初始化设置

首次使用时，运行 `/daida-ai:relief-pitcher-ai` 后会提示执行设置脚本。
按照 Claude 的指引，批准以下命令：

```bash
bash <plugin-dir>/skills/relief-pitcher-ai/scripts/setup.sh
```

该脚本将创建 Python 虚拟环境并安装所有依赖。

## 使用方法

在 Claude Code 中调用：

```
/daida-ai:relief-pitcher-ai
```

也可以用自然语言请求：

- "帮我做一个演讲PPT"
- "生成演示文稿"
- "救场！帮我准备发表材料"

### 工作流程

系统会交互式地询问：

1. **主题**：演讲内容是什么
2. **受众**：面向谁演讲
3. **时长**：几分钟（默认 5 分钟）
4. **模板**：`tech` / `casual` / `formal`
5. **TTS 引擎**：`edge`（默认）/ `voicevox`

全自动执行完整流程：大纲 → 幻灯片 → 演讲稿 → 语音合成 → 音频嵌入 → 幻灯片放映设置。

### 帮助

输入"帮助"、"使用说明"或"流程是什么？"可以查看完整的流程图。

### 从指定步骤重新开始

如果中途修改了 PPTX 或 TTS 脚本，可以指定"从第 4 步重新开始"来恢复执行。

常见示例：
- 手动修改 PPTX 后 → "从第 4 步重新开始"以重新生成音频
- 修正发音后 → "从第 4c 步重新开始"仅重新合成音频
- 更换模板 → "从第 2 步重新开始"以重新生成幻灯片

### 修正 TTS 发音

如果 TTS 产生了错误的读音，可以通过以下方式修正：

- **发音词典**：在 `skills/relief-pitcher-ai/assets/pronunciation_dict.tsv` 中定义替换规则（导出时自动应用）
- **手动修改**：导出 TTS 脚本后在文本编辑器中直接修改

## 模板

| 模板 | 风格 | 字体 |
|------|------|------|
| `tech` | 深色主题，青色强调 | Noto Sans CJK JP |
| `casual` | 暖色调，圆润设计 | Noto Sans CJK JP |
| `formal` | 白底，商务风格 | Noto Serif CJK JP / Noto Sans CJK JP |

> **注意**：模板目前针对日语内容优化。使用其他语言时，系统字体将作为后备。如需中文最佳显示效果，建议安装 Noto Sans CJK SC。

## 语音合成引擎

| 引擎 | 说明 | 备注 |
|------|------|------|
| edge-tts | Microsoft Edge TTS，无需安装，支持多语言 | 默认 |
| VOICEVOX | 角色语音（如 Zundamon），日语 TTS 引擎 | 需要运行 [VOICEVOX Engine](https://voicevox.hiroshiba.jp/) |

## 验证

以下验证会自动应用于幻灯片规格 JSON（由 LLM 生成）：

- 幻灯片数量（1–20 张）
- 布局与字段一致性（例如 `two_content` 必须包含 `left`/`right`）
- 文本长度上限（标题 100 字，正文项目 200 字等）
- 音频文件格式（MP3/WAV）和大小（最大 50 MB）
- 预估发言时长检查

## 注意事项

### 在 LibreOffice Impress 中播放

自动翻页（音频播放结束后自动跳转到下一张幻灯片）**仅在 PowerPoint（Windows / macOS）中有效**。

**LibreOffice Impress 不支持自动翻页**。这是 LibreOffice 无法正确处理 PPTX 时间设置（`advTm`）的已知限制（[Bug 101527](https://bugs.documentfoundation.org/show_bug.cgi?id=101527)）。

使用 LibreOffice Impress 时：
- **手动**翻页（点击或方向键）
- 或在 LibreOffice 的"幻灯片切换"面板中手动设置自动切换时间

### 关于字体

模板使用 [Noto CJK](https://github.com/googlefonts/noto-cjk) 字体显示日文文本。
适用于 Windows、macOS 和 Linux。如未安装，将使用操作系统默认字体。
如需中文最佳显示效果，建议安装 Noto Sans CJK SC。

## 许可证

MIT

---

> 本文档是 [README.md](./README.md) 的中文翻译。如有差异，以英文版为准。
