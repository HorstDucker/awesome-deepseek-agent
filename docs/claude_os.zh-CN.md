[English](./claude_os.md) | [简体中文](./claude_os.zh-CN.md) | [Deutsch](./claude_os.de.md) · [← 返回](../README.zh-CN.md)

# ClaudeOS

一个用纯 Python 实现的极简、AI 原生操作系统 —— 零外部依赖。  
ClaudeOS 在一个小巧的内核之上提供了类 Unix 的 shell，内核负责管理内存、进程、虚拟文件系统、cron 调度器、内存中的密钥保险库，以及具名的后台代理（coworkers）。

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Shell (REPL)                               │
│  mem  fs  ps  cron  coworker  secret  sched  stats  history  help  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ syscalls
┌───────────────────────────────▼─────────────────────────────────────┐
│                              Kernel                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────┐  ┌──────────┐  ┌─────────┐  │
│  │MemoryBus │  │ProcessTbl│  │  VFS │  │CronDaemon│  │SecretVlt│  │
│  │short-term│  │ READY    │  │/tmp  │  │interval  │  │in-memory│  │
│  │long-term │  │ RUNNING  │  │/home │  │jobs (bg) │  │never log│  │
│  │ (JSON)   │  │ DONE     │  │/etc  │  └──────────┘  └─────────┘  │
│  └──────────┘  └──────────┘  └──────┘  ┌──────────────────────┐   │
│                                         │  CoworkerRegistry    │   │
│                                         │  named agents +      │   │
│                                         │  secret injection    │   │
│                                         └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 组件

| 组件 | 文件 | 作用 |
|------|------|------|
| Kernel | `claude_os/kernel.py` | 系统调用表、子系统装配、启动/关闭 |
| MemoryBus | `claude_os/memory.py` | 两级键值存储（易失内存 + 持久化 JSON） |
| VirtualFS | `claude_os/fs.py` | 内存中的 POSIX 风格文件系统 |
| ProcessTable | `claude_os/process.py` | 轻量级协作式进程模型 |
| Scheduler | `claude_os/scheduler.py` | 带后台守护线程的 FIFO 队列 |
| CronDaemon | `claude_os/cron.py` | 基于时间间隔的后台任务调度器 |
| SecretVault | `claude_os/secrets.py` | 线程安全的内存凭据存储 |
| CoworkerRegistry | `claude_os/coworker.py` | 带密钥注入的具名后台代理 |
| Shell | `claude_os/shell.py` | 提供 Unix 风格命令的交互式 REPL |

## 安装

无依赖 —— 需要 Python 3.9+。

```bash
git clone https://github.com/horstducker/awesome-deepseek-agent.git
cd awesome-deepseek-agent
python run_os.py
```

## 入口脚本

| 脚本 | 说明 |
|------|------|
| `python run_os.py` | 交互式 shell（REPL） |
| `python web_dashboard.py` | 实时 Web 仪表盘，地址 `http://localhost:8080` |
| `python dashboard.py` | ANSI 终端仪表盘（每秒刷新） |
| `python snes_os.py` | 圣剑传说版 —— 8 个元素 coworker，SNES 风格 TUI |
| `python run_cron.py` | 无头 CI 模式 —— 从环境变量加载密钥，触发所有 coworker |

## 快速上手

```
   ___  _                 _        ___  ____
  / __\| |  __ _  _   _ | |  ___ / _ \/ ___|
 / /   | | / _` || | | || | / _ \ | | \___ \
/ /___ | || (_| || |_| || ||  __/ |_| |___) |
\____/ |_| \__,_| \__,_||_| \___|\___/|____/

  AI-Native Operating System  •  kernel v0.1.0
  Type 'help' for available commands.

claude@os:~$ remember name "Claude" --persist
  stored 'name' in long-term memory

claude@os:~$ secret set OPENAI_API_KEY sk-abc123
  secret OPENAI_API_KEY stored

claude@os:~$ secret get OPENAI_API_KEY
  OPENAI_API_KEY = ***

claude@os:~$ coworker add fetcher 30s OPENAI_API_KEY
  coworker 'fetcher' registered (job #1) — runs every 30s
  uses secrets: OPENAI_API_KEY

claude@os:~$ cron list
    ID  NAME                  INTERVAL      RUNS  LAST RUN    EN   ERROR
     1  fetcher               30s              0  never       yes

claude@os:~$ coworker fire fetcher
  coworker 'fetcher' triggered
```

## Shell 命令

### 内存（Memory）
| 命令 | 说明 |
|------|------|
| `mem` | 列出当前内存中的所有键 |
| `remember <key> <value> [--persist]` | 存储一个值；`--persist` 可在重启后保留 |
| `recall <key>` | 取回已存储的值 |
| `forget <key>` | 从内存中删除某个键（不存在时报告 `not found`） |

底层这些命令映射到内存系统调用：`mem_read`、`mem_write`、`mem_delete` 和 `mem_list`。`forget` 通过 `mem_delete` 实现，删除成功返回 `True`，键不存在则返回 `False` —— 因此每次删除都可通过系统调用表审计。

### 文件系统（Filesystem）
| 命令 | 说明 |
|------|------|
| `ls [path]` | 列出目录内容 |
| `cat <path>` | 打印文件内容 |
| `write <path> <text>` | 创建或覆盖文件 |
| `rm <path>` | 删除文件 |
| `cd [path]` | 切换工作目录 |
| `pwd` | 打印当前工作目录 |

### 进程（Processes）
| 命令 | 说明 |
|------|------|
| `ps [status]` | 列出进程（可按状态过滤） |
| `spawn <name> [msg]` | 创建并排入一个后台进程 |
| `kill <pid>` | 终止某个进程 |

### Cron 调度器
| 命令 | 说明 |
|------|------|
| `cron list` | 列出所有计划任务 |
| `cron add <name> <interval> <command…>` | 按时间间隔调度一条 shell 命令（例如 `cron add heartbeat 10s write /var/log/hb.txt tick`） |
| `cron log [n]` | 显示最近 n 条触发事件（默认 10 条） |
| `cron enable <id>` | 启用任务 |
| `cron disable <id>` | 禁用任务 |
| `cron run <id>` | 立即触发任务 |
| `cron remove <id>` | 移除任务（别名：`cron rm <id>`） |

时间间隔格式：`30s`、`5m`、`2h`、`1d`。被调度的命令可以是任意内置 shell 命令；当间隔到达时由 cron 守护进程重放执行。`secret` 和 `coworker` 同样接受 `rm` 作为 `delete`/`remove` 的别名。

### 密钥（Secrets）
| 命令 | 说明 |
|------|------|
| `secret list` | 列出密钥名称（绝不显示值） |
| `secret set <NAME> <VALUE>` | 在内存中存储一个密钥 |
| `secret get <NAME>` | 确认存在性 —— 始终打印 `***` |
| `secret delete <NAME>` | 删除一个密钥 |
| `secret env` | 从匹配 `*_API_KEY` 或 `CLAUDE_SECRET_*` 的环境变量加载密钥 |

密钥值**绝不**写入磁盘、绝不打印，也绝不出现在命令历史中。

### Coworkers（后台代理）
| 命令 | 说明 |
|------|------|
| `coworker list` | 列出所有已注册的 coworker |
| `coworker add <NAME> <SCHEDULE> [SECRETS…]` | 注册一个示例 coworker |
| `coworker remove <NAME>` | 注销一个 coworker |
| `coworker fire <NAME>` | 立即运行 |
| `coworker enable <NAME>` | 启用 |
| `coworker disable <NAME>` | 禁用 |

### 系统（System）
| 命令 | 说明 |
|------|------|
| `sched` | 显示调度器状态和最近日志 |
| `stats` | 内核统计信息 |
| `history` | 命令历史 |
| `exit` / `quit` | 关闭并退出 |

## 圣剑传说版（Secret of Mana Edition）

`snes_os.py` 是一个独立的 16 位 SNES 风格终端界面，运行 8 个相互独立的元素 coworker，灵感来自《圣剑传说》（*Secret of Mana*）中的精灵。

```bash
python snes_os.py
```

操作：`1-8` 选择精灵 · `F` 立即触发 · `E` 启用 · `D` 禁用 · `Q` 退出

### 8 个玛娜精灵

| # | 精灵 | 元素 | 调度间隔 | 行为 |
|---|------|------|----------|------|
| 1 | Undine | 水 | 8s | 跟踪内存键数量 |
| 2 | Gnome | 土 | 12s | 写入虚拟文件系统日志 |
| 3 | Sylphid | 风 | 5s | 最快的运行者，阵风计数 |
| 4 | Salamando | 火 | 10s | 脉冲式输出内核系统调用统计 |
| 5 | Lumina | 光 | 20s | 校验密钥保险库完整性 |
| 6 | Shade | 暗 | 15s | 扫描触发日志中的错误 |
| 7 | Luna | 月 | 30s | 心跳与运行时长跟踪 |
| 8 | Dryad | 木 | 25s | 内存统计与清理 |

每个精灵按自己的调度独立运行，彼此完全独立。界面以 2×4 的精灵卡片网格显示，带有 HP 血条样式的运行计数器和实时触发日志。

## Web 仪表盘

```bash
python web_dashboard.py          # serves on http://localhost:8080
python web_dashboard.py --port 9090
python web_dashboard.py --quiet  # no demo jobs
```

仪表盘每秒轮询一次 `/api/state`，显示内核统计、密钥（已掩码）、内存、cron 任务、coworker 以及触发日志 —— 全部呈现在深色主题的浏览器 UI 中。

## DeepSeek 模型配置

ClaudeOS 本身零依赖、不调用任何模型，但它的 coworker 和无头 cron 运行被设计为通过其密钥注入的 action 来驱动 [DeepSeek](https://platform.deepseek.com/) 模型。将 coworker 接入 DeepSeek API 时，适用以下参数（价格以每 100 万 tokens 的美元计，截至 2026 年 6 月 —— 请在[价格页面](https://api-docs.deepseek.com/quick_start/pricing)核对最新费率）：

| 模型 | 上下文 | 最大输出 | 输入（缓存未命中） | 输入（缓存命中） | 输出 |
|------|-------:|---------:|-------------------:|-----------------:|-----:|
| **DeepSeek-V4-Pro** | 1,048,576 (1M) | 384,000 | $1.74 | ~$0.174 | $3.48 |
| **DeepSeek-V4-Flash** | 1,048,576 (1M) | 384,000 | $0.14 | ~$0.014 | $0.28 |

- **1M 上下文**（`context_length: 1000000`）自 V4 发布以来已成为所有官方 DeepSeek 服务的默认值。
- **思考 / 推理模式（Thinking）** 受支持且默认开启（按输出计费）。通过兼容 OpenAI 的 SDK，可用 `extra_body={"thinking": {"type": "enabled"}}` 切换，并用 `reasoning_effort`（`"high"` 或表示最大推理的 `"xhigh"`）调节深度。思维链通过 `reasoning_content` 返回，与 `content` 同级（流式输出为 `delta.reasoning_content`）。与推理不兼容的采样参数会被自动从请求中剔除。
- 旧模型名 `deepseek-chat` / `deepseek-reasoner` 自 2026-07-24 起弃用，由 V4 模型家族取代。

将密钥作为 secret 存储（`secret set DEEPSEEK_API_KEY …` 或 `secret env`），并在 coworker 上声明它，使注册表仅在调用时注入：

```
claude@os:~$ secret set DEEPSEEK_API_KEY sk-...
claude@os:~$ coworker add reporter 1h DEEPSEEK_API_KEY
```

## GitHub Actions / 无头 CI

`run_cron.py` 是用于定时 CI 运行的无头入口：

```bash
DEEPSEEK_API_KEY=sk-... python run_cron.py
```

仓库自带的 `.github/workflows/cron-worker.yml` 每天 08:00 UTC 运行，并支持 `workflow_dispatch`。它会从仓库 secrets 注入 `DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 和 `ANTHROPIC_API_KEY`。

## 扩展 ClaudeOS

### 注册自定义系统调用

```python
from claude_os import Kernel, Shell

kernel = Kernel()
kernel.boot()

kernel.register_syscall("greet", lambda name: f"Hello, {name}!")

shell = Shell(kernel)
shell.run()
```

### 以编程方式注册 coworker

```python
def my_agent(secrets: dict) -> str:
    api_key = secrets.get("MY_API_KEY", "")
    # do work with api_key
    return "done"

kernel.coworkers.register(
    name="my-agent",
    schedule="5m",
    secret_names=["MY_API_KEY"],
    action=my_agent,
)
```

## 运行测试

```bash
python -m claude_os.tests
```

## 设计决策

- **纯 Python，零依赖** —— 在任何有 Python 3.9+ 的环境都能运行。
- **协作式多任务** —— 进程自然让出，没有抢占。
- **两级内存** —— 短期（dict）用于临时状态，长期（JSON 文件）用于持久化。密钥只存在于短期层，绝不写入 JSON。
- **系统调用表** —— 所有命令都经过 `kernel.syscall()`，使每个操作都可审计、可扩展。
- **密钥隔离** —— `SecretVault` 线程安全；值在任何地方都被掩码为 `***`，包括 cron 触发日志和命令历史。
- **用 coworker 而非裸 cron** —— coworker 显式声明其密钥依赖；注册表在调用时解析它们，而非注册时。
