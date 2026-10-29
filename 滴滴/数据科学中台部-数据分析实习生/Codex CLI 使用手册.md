# Codex CLI 使用手册

> 适用范围：在终端中使用 OpenAI Codex 读取项目、修改文件、运行命令和审查代码。命令会随版本变化；遇到差异时以 `codex --help` 和 `codex <子命令> --help` 为准。

## 1. 安装与登录

先安装 Node.js 和 npm，然后运行：

```powershell
npm install -g @openai/codex@latest
codex --version
codex login
```

`codex login` 会引导完成身份验证。登录状态可用 `codex login status` 检查。也可以直接运行 `codex`，按首次启动提示登录。更新可运行 `codex update`，或重新执行 npm 安装命令。

## 2. 第一次使用

在 PowerShell 中进入项目目录：

```powershell
cd "C:\path\to\your\project"
codex
```

进入交互界面后，用自然语言说明目标、相关文件和验收条件。例如：

```text
阅读这个项目，说明目录结构和启动方式；先不要修改文件。
```

```text
修复登录页提交后重复请求的问题。定位原因、修改代码，并运行相关测试。
```

也可以直接带初始任务启动：

```powershell
codex "总结当前目录中的 Markdown 笔记"
```

Codex 会以当前目录作为工作根目录。使用 `-C` 指定其他目录：

```powershell
codex -C "C:\path\to\your\project" "检查项目中的 TODO"
```

## 3. 常用命令速查

| 命令 | 用途 |
| --- | --- |
| `codex` | 启动交互会话 |
| `codex "任务"` | 带任务启动交互会话 |
| `codex exec "任务"` | 非交互执行一次任务，适合脚本 |
| `codex review` | 非交互代码审查 |
| `codex resume` | 选择并继续以前的会话 |
| `codex resume --last` | 继续最近的会话 |
| `codex fork` | 从已有会话分叉新会话 |
| `codex login` / `codex logout` | 登录 / 清除本地认证信息 |
| `codex mcp` | 管理 MCP 服务 |
| `codex doctor` | 诊断安装、配置和认证问题 |
| `codex --help` | 查看当前安装版本支持的选项 |

具体子命令参数请运行 `codex exec --help`、`codex review --help` 等查看。

### 交互会话中的常用命令

启动 `codex` 后，在输入框键入 `/` 可查看当前版本可用的命令。下表中的斜杠命令是在 Codex 会话内输入，不是在 PowerShell 中直接运行。

| 命令 | 用途 |
| --- | --- |
| `/help` | 查看会话内帮助（若当前版本提供） |
| `/status` | 查看模型、权限、上下文和会话状态 |
| `/model` | 切换当前会话的模型 |
| `/permissions` | 调整当前会话的权限与批准方式 |
| `/plan` | 进入计划模式，先讨论实施方案 |
| `/review` | 审查当前工作区的代码变更 |
| `/diff` | 查看 Codex 修改的 Git 差异 |
| `/compact` | 压缩较长对话的上下文 |
| `/new` | 在 CLI 中开始新会话 |
| `/resume` | 继续已保存的会话 |
| `/fork` | 从当前会话分叉新会话 |
| `/init` | 在当前项目生成 `AGENTS.md` 初稿 |
| `/mcp` | 查看已连接的 MCP 服务 |
| `/skills` | 浏览可用技能 |
| `/pwd` | 查看当前工作目录 |
| `/cd <路径>` | 切换工作目录 |
| `/export` | 将会话导出为 Markdown |
| `/exit` | 退出 Codex CLI |

输入 `@` 可以搜索并引用项目文件；在输入行开头使用 `!` 可以运行本地 Shell 命令。Codex 工作时按 `Enter` 可补充当前任务的指令，按 `Tab` 可将内容排入下一轮。具体可用命令以输入 `/` 后出现的菜单为准。

## 4. 常用启动选项

```powershell
codex -m <模型名>                         # 指定模型
codex -s read-only "分析项目结构"          # 只读沙箱
codex -s workspace-write "修复测试"       # 允许在工作区写入
codex -i .\screenshot.png "解释这个报错"  # 附加图片
codex --search "核对最新官方文档"          # 开启实时网页搜索
codex --worktree "实现新功能"             # 在新 Git worktree 中工作
```

`read-only`、`workspace-write` 和 `danger-full-access` 是沙箱模式。日常项目修改通常使用 `workspace-write`。涉及工作区之外的写入或其他受限操作时，Codex 可能请求批准。`--ask-for-approval on-request` 由模型按需请求批准；`never` 不会请求批准，失败会返回给模型。不要在普通本机项目中使用 `--dangerously-bypass-approvals-and-sandbox`。

## 5. 非交互任务与代码审查

```powershell
codex exec "检查 README 中的安装步骤是否与项目文件一致，并修正错误"
codex review
```

非交互模式适合明确、可一次完成的任务。脚本中使用前，应先确认当前版本的参数和退出状态。代码审查会分析变更并报告发现；需要指定审查范围时查看 `codex review --help`。

## 6. 配置

用户配置通常位于 `~/.codex/config.toml`，Windows 对应用户目录下的 `.codex\config.toml`。可用 `-c` 临时覆盖单项配置，键支持点号路径，值按 TOML 解析：

```powershell
codex -c 'model="<模型名>"'
```

常用命令行选项优先用 `-m`、`-s`、`-C` 等专用参数。修改配置前先参考官方配置文档，并用 `codex --help` 核对本机版本。

## 7. 写出更有效的任务

任务描述建议包含四项：目标、范围、约束、验收方式。

```text
目标：修复订单汇总结果偶尔重复的问题。
范围：只修改数据处理模块和相关测试。
约束：保持公开函数签名不变。
验收：运行对应测试，并说明根因、修改点和剩余风险。
```

较大的任务可以先让 Codex 阅读代码并提出方案，再让它实施。完成后检查 `git diff`、测试输出和最终说明；关键改动仍需人工复核。

## 8. 常见问题

- **找不到 `codex` 命令**：确认 npm 全局安装成功，并检查 npm 全局可执行目录是否在 `PATH` 中；重新打开终端再试。
- **登录失败**：运行 `codex doctor` 检查认证与运行环境；确认网络和账户访问正常。
- **命令参数不匹配**：运行 `codex --version` 与 `codex <子命令> --help`；CLI 更新后参数可能改变。
- **无法修改文件**：确认当前工作目录正确、沙箱允许写入，并按提示批准必要操作。
- **会话中断**：运行 `codex resume`，或用 `codex resume --last` 继续最近会话。

## 官方资料

- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [开发者命令参考](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [配置基础](https://learn.chatgpt.com/docs/config-file/config-basic)

本文依据 OpenAI Docs 和本机 `codex --help` 整理，最后核对日期：2026-10-29。
