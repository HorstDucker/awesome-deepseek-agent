[English](./claude_os.md) | [简体中文](./claude_os.zh-CN.md) | [Deutsch](./claude_os.de.md) · [← Back](../README.md)

# ClaudeOS

A minimal, AI-native operating system implemented in pure Python — zero external dependencies.  
ClaudeOS provides a Unix-inspired shell on top of a tiny kernel that manages memory, processes, a virtual filesystem, a cron scheduler, an in-memory secret vault, and named background agents (coworkers).

## Architecture

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

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Kernel | `claude_os/kernel.py` | Syscall table, subsystem wiring, boot/shutdown |
| MemoryBus | `claude_os/memory.py` | Two-tier key-value store (volatile + persisted JSON) |
| VirtualFS | `claude_os/fs.py` | In-memory POSIX-style filesystem |
| ProcessTable | `claude_os/process.py` | Lightweight cooperative process model |
| Scheduler | `claude_os/scheduler.py` | FIFO queue with background daemon thread |
| CronDaemon | `claude_os/cron.py` | Interval-based background task scheduler |
| SecretVault | `claude_os/secrets.py` | Thread-safe in-memory credential store |
| CoworkerRegistry | `claude_os/coworker.py` | Named background agents with secret injection |
| Shell | `claude_os/shell.py` | Interactive REPL with Unix-style commands |

## Installation

No dependencies — requires Python 3.9+.

```bash
git clone https://github.com/horstducker/awesome-deepseek-agent.git
cd awesome-deepseek-agent
python run_os.py
```

## Entry Points

| Script | Description |
|--------|-------------|
| `python run_os.py` | Interactive shell (REPL) |
| `python web_dashboard.py` | Live web dashboard on `http://localhost:8080` |
| `python dashboard.py` | ANSI terminal dashboard (1s refresh) |
| `python snes_os.py` | Secret of Mana edition — 8 elemental coworkers, SNES TUI |
| `python run_cron.py` | Headless CI mode — loads secrets from env, fires all coworkers |

## Quick Start

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

## Shell Commands

### Memory
| Command | Description |
|---------|-------------|
| `mem` | List all keys currently in memory |
| `remember <key> <value> [--persist]` | Store a value; `--persist` survives restarts |
| `recall <key>` | Retrieve a stored value |
| `forget <key>` | Delete a key from memory (reports `not found` if absent) |

Under the hood these map to memory syscalls: `mem_read`, `mem_write`,
`mem_delete`, and `mem_list`. `forget` routes through `mem_delete`,
which returns `True` when a key was removed and `False` when it did not
exist — so every deletion stays auditable through the syscall table.

### Filesystem
| Command | Description |
|---------|-------------|
| `ls [path]` | List directory contents |
| `cat <path>` | Print file contents |
| `write <path> <text>` | Create or overwrite a file |
| `rm <path>` | Delete a file |
| `cd [path]` | Change working directory |
| `pwd` | Print working directory |

### Processes
| Command | Description |
|---------|-------------|
| `ps [status]` | List processes (optionally filter by status) |
| `spawn <name> [msg]` | Create and queue a background process |
| `kill <pid>` | Terminate a process |

### Cron Scheduler
| Command | Description |
|---------|-------------|
| `cron list` | List all scheduled jobs |
| `cron add <name> <interval> <command…>` | Schedule a shell command to run on an interval (e.g. `cron add heartbeat 10s write /var/log/hb.txt tick`) |
| `cron log [n]` | Show last n fire events (default 10) |
| `cron enable <id>` | Enable a job |
| `cron disable <id>` | Disable a job |
| `cron run <id>` | Fire a job immediately |
| `cron remove <id>` | Remove a job (alias: `cron rm <id>`) |

Interval formats: `30s`, `5m`, `2h`, `1d`. The scheduled command is any built-in shell command; it is replayed by the cron daemon when the interval elapses. `secret` and `coworker` also accept `rm` as an alias for `delete`/`remove`.

### Secrets
| Command | Description |
|---------|-------------|
| `secret list` | List secret names (values never shown) |
| `secret set <NAME> <VALUE>` | Store a secret in-memory |
| `secret get <NAME>` | Confirm presence — always prints `***` |
| `secret delete <NAME>` | Remove a secret |
| `secret env` | Load secrets from env vars matching `*_API_KEY` or `CLAUDE_SECRET_*` |

Secret values are **never** persisted to disk, never printed, and never appear in command history.

### Coworkers
| Command | Description |
|---------|-------------|
| `coworker list` | List all registered coworkers |
| `coworker add <NAME> <SCHEDULE> [SECRETS…]` | Register a demo coworker |
| `coworker remove <NAME>` | Unregister a coworker |
| `coworker fire <NAME>` | Run immediately |
| `coworker enable <NAME>` | Enable |
| `coworker disable <NAME>` | Disable |

### System
| Command | Description |
|---------|-------------|
| `sched` | Show scheduler status and recent log |
| `stats` | Kernel statistics |
| `history` | Command history |
| `exit` / `quit` | Shutdown and quit |

## Secret of Mana Edition

`snes_os.py` is a standalone 16-bit SNES-style terminal interface that runs 8 independent elemental coworkers inspired by the Mana spirits from *Secret of Mana*.

```bash
python snes_os.py
```

Controls: `1-8` select spirit · `F` fire now · `E` enable · `D` disable · `Q` quit

### The 8 Mana Spirits

| # | Spirit | Element | Schedule | Action |
|---|--------|---------|------------|--------|
| 1 | Undine | Water | 8s | Tracks memory key count |
| 2 | Gnome | Earth | 12s | Logs to virtual filesystem |
| 3 | Sylphid | Wind | 5s | Fastest runner, gusts counter |
| 4 | Salamando | Fire | 10s | Pulses kernel syscall stats |
| 5 | Lumina | Light | 20s | Verifies secret vault integrity |
| 6 | Shade | Dark | 15s | Scans fire log for errors |
| 7 | Luna | Moon | 30s | Heartbeat & uptime tracker |
| 8 | Dryad | Wood | 25s | Memory stats & cleanup |

Each spirit runs on its own schedule, fully independent of the others. The display shows a 2×4 grid of spirit cards with HP-bar-style run counters and a live fire log.

## Web Dashboard

```bash
python web_dashboard.py          # serves on http://localhost:8080
python web_dashboard.py --port 9090
python web_dashboard.py --quiet  # no demo jobs
```

The dashboard polls `/api/state` every second and displays kernel stats, secrets (masked), memory, cron jobs, coworkers, and the fire log — all in a dark-theme browser UI.

## DeepSeek Model Configuration

ClaudeOS itself is dependency-free and does not call any model, but its coworkers
and headless cron runs are designed to drive [DeepSeek](https://platform.deepseek.com/)
models through their secret-injected actions. When wiring a coworker to the
DeepSeek API, the following parameters apply (prices in USD per 1M tokens, as of
June 2026 — verify current rates on the [pricing page](https://api-docs.deepseek.com/quick_start/pricing)):

| Model | Context | Max output | Input (cache miss) | Input (cache hit) | Output |
|-------|--------:|-----------:|-------------------:|------------------:|-------:|
| **DeepSeek-V4-Pro** | 1,048,576 (1M) | 384,000 | $1.74 | ~$0.174 | $3.48 |
| **DeepSeek-V4-Flash** | 1,048,576 (1M) | 384,000 | $0.14 | ~$0.014 | $0.28 |

- **1M context** (`context_length: 1000000`) is the default across all official
  DeepSeek services since the V4 release.
- **Thinking / reasoning mode** is supported and on by default (billed as output).
  Via the OpenAI-compatible SDK, toggle it with
  `extra_body={"thinking": {"type": "enabled"}}` and tune depth with
  `reasoning_effort` (`"high"` or `"xhigh"` for maximum reasoning). The chain of
  thought is returned as `reasoning_content`, at the same level as `content`
  (streamed as `delta.reasoning_content`). Sampling parameters incompatible with
  reasoning are dropped from the request automatically.
- The legacy model names `deepseek-chat` / `deepseek-reasoner` are deprecated
  as of 2026-07-24 in favour of the V4 model family.

Store the key as a secret (`secret set DEEPSEEK_API_KEY …` or `secret env`) and
declare it on the coworker so the registry injects it only at call time:

```
claude@os:~$ secret set DEEPSEEK_API_KEY sk-...
claude@os:~$ coworker add reporter 1h DEEPSEEK_API_KEY
```

## GitHub Actions / Headless CI

`run_cron.py` is the headless entry point for scheduled CI runs:

```bash
DEEPSEEK_API_KEY=sk-... python run_cron.py
```

The included `.github/workflows/cron-worker.yml` runs daily at 08:00 UTC and supports `workflow_dispatch`. It injects `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` from repository secrets.

## Extending ClaudeOS

### Register a custom syscall

```python
from claude_os import Kernel, Shell

kernel = Kernel()
kernel.boot()

kernel.register_syscall("greet", lambda name: f"Hello, {name}!")

shell = Shell(kernel)
shell.run()
```

### Register a coworker programmatically

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

## Running Tests

```bash
python -m claude_os.tests
```

## Design Decisions

- **Pure Python, zero deps** — runs anywhere Python 3.9+ is available.
- **Cooperative multitasking** — processes yield naturally; no preemption.
- **Two-tier memory** — short-term (dict) for transient state, long-term (JSON file) for persistence. Secrets live only in the short-term tier and are never written to JSON.
- **Syscall table** — all commands go through `kernel.syscall()`, making every action auditable and extensible.
- **Secret isolation** — `SecretVault` is thread-safe; values are masked as `***` everywhere including the cron fire log and command history.
- **Coworkers over raw cron** — coworkers declare their secret dependencies explicitly; the registry resolves them at call time, never at registration time.

*Created by Grille with Claude Code*
