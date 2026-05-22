"""
ClaudeOS Shell — interactive REPL on top of the kernel.

Built-in commands mirror a POSIX shell but all operations go through
the kernel syscall interface so every action is auditable.
"""

from __future__ import annotations

import json
import shlex
import sys
import time
from typing import Dict, List, Optional

from .kernel import Kernel


class Shell:
    PS1 = "claude@os:~$ "

    def __init__(self, kernel: Kernel) -> None:
        self.kernel = kernel
        self._history: List[str] = []
        self._cwd = "/"
        self._commands = {
            # memory
            "mem":      self._cmd_mem,
            "remember": self._cmd_remember,
            "recall":   self._cmd_recall,
            "forget":   self._cmd_forget,
            # filesystem
            "ls":       self._cmd_ls,
            "cat":      self._cmd_cat,
            "write":    self._cmd_write,
            "rm":       self._cmd_rm,
            "cd":       self._cmd_cd,
            "pwd":      self._cmd_pwd,
            # processes
            "ps":       self._cmd_ps,
            "spawn":    self._cmd_spawn,
            "kill":     self._cmd_kill,
            # scheduler
            "sched":    self._cmd_sched,
            # system
            "stats":    self._cmd_stats,
            "history":  self._cmd_history,
            "help":     self._cmd_help,
            "exit":     self._cmd_exit,
            "quit":     self._cmd_exit,
        }

    def run(self) -> None:
        while True:
            try:
                line = input(self.PS1).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            self._history.append(line)
            self._dispatch(line)

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, line: str) -> None:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            print(f"  parse error: {exc}")
            return
        cmd, *args = parts
        handler = self._commands.get(cmd)
        if handler is None:
            print(f"  {cmd}: command not found — type 'help' for a list")
            return
        try:
            handler(args)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"  error: {exc}")

    # ------------------------------------------------------------------
    # Memory commands
    # ------------------------------------------------------------------

    def _cmd_mem(self, args: List[str]) -> None:
        dump = self.kernel.syscall("mem_list")
        if not dump:
            print("  (memory is empty)")
            return
        for key in dump:
            val = self.kernel.syscall("mem_read", key)
            print(f"  {key} = {val!r}")

    def _cmd_remember(self, args: List[str]) -> None:
        if len(args) < 2:
            print("  usage: remember <key> <value> [--persist]")
            return
        persist = "--persist" in args
        if persist:
            args = [a for a in args if a != "--persist"]
        key, value = args[0], " ".join(args[1:])
        self.kernel.syscall("mem_write", key, value, persist=persist)
        tier = "long-term" if persist else "short-term"
        print(f"  stored {key!r} in {tier} memory")

    def _cmd_recall(self, args: List[str]) -> None:
        if not args:
            print("  usage: recall <key>")
            return
        val = self.kernel.syscall("mem_read", args[0])
        if val is None:
            print(f"  {args[0]!r}: not found")
        else:
            print(f"  {args[0]} = {val!r}")

    def _cmd_forget(self, args: List[str]) -> None:
        if not args:
            print("  usage: forget <key>")
            return
        ok = self.kernel.syscall("mem_write", args[0], None)
        self.kernel.memory.delete(args[0])
        print(f"  {args[0]!r} removed from memory")

    # ------------------------------------------------------------------
    # Filesystem commands
    # ------------------------------------------------------------------

    def _cmd_ls(self, args: List[str]) -> None:
        path = args[0] if args else self._cwd
        entries = self.kernel.syscall("fs_list", path)
        if not entries:
            print(f"  (empty)")
            return
        for e in sorted(entries, key=lambda x: x["name"]):
            tag = "/" if e["type"] == "dir" else ""
            size = f"  {e['size']}B" if e["type"] == "file" else ""
            print(f"  {e['name']}{tag}{size}")

    def _cmd_cat(self, args: List[str]) -> None:
        if not args:
            print("  usage: cat <path>")
            return
        path = self._resolve(args[0])
        content = self.kernel.syscall("fs_read", path)
        if content is None:
            print(f"  {args[0]}: no such file")
        else:
            print(content)

    def _cmd_write(self, args: List[str]) -> None:
        if len(args) < 2:
            print("  usage: write <path> <content…>")
            return
        path = self._resolve(args[0])
        content = " ".join(args[1:])
        self.kernel.syscall("fs_write", path, content)
        print(f"  written {len(content)}B to {path}")

    def _cmd_rm(self, args: List[str]) -> None:
        if not args:
            print("  usage: rm <path>")
            return
        path = self._resolve(args[0])
        ok = self.kernel.syscall("fs_delete", path)
        if ok:
            print(f"  deleted {path}")
        else:
            print(f"  {args[0]}: no such file")

    def _cmd_cd(self, args: List[str]) -> None:
        self._cwd = self._resolve(args[0]) if args else "/"
        print(f"  cwd → {self._cwd}")

    def _cmd_pwd(self, args: List[str]) -> None:
        print(f"  {self._cwd}")

    # ------------------------------------------------------------------
    # Process commands
    # ------------------------------------------------------------------

    def _cmd_ps(self, args: List[str]) -> None:
        status_filter = args[0] if args else None
        procs = self.kernel.syscall("proc_list")
        if status_filter:
            procs = [p for p in procs if p["status"] == status_filter]
        if not procs:
            print("  (no processes)")
            return
        print(f"  {'PID':>5}  {'NAME':<24}  {'STATUS':<10}  CREATED")
        for p in procs:
            ts = time.strftime("%H:%M:%S", time.localtime(p["created_at"]))
            print(f"  {p['pid']:>5}  {p['name']:<24}  {p['status']:<10}  {ts}")

    def _cmd_spawn(self, args: List[str]) -> None:
        if not args:
            print("  usage: spawn <name>  (spawns a demo echo process)")
            return
        name = args[0]
        msg = " ".join(args[1:]) if len(args) > 1 else f"process '{name}' completed"

        def _task(message: str) -> str:
            time.sleep(0.05)
            return message

        pid = self.kernel.syscall("proc_spawn", name, _task, msg)
        self.kernel.syscall("sched_queue", pid)
        print(f"  spawned pid={pid} name={name!r}")

    def _cmd_kill(self, args: List[str]) -> None:
        if not args or not args[0].isdigit():
            print("  usage: kill <pid>")
            return
        ok = self.kernel.syscall("proc_kill", int(args[0]))
        if ok:
            print(f"  process {args[0]} killed")
        else:
            print(f"  pid {args[0]}: not found")

    # ------------------------------------------------------------------
    # Scheduler commands
    # ------------------------------------------------------------------

    def _cmd_sched(self, args: List[str]) -> None:
        info = self.kernel.syscall("sched_status")
        print(json.dumps(info, indent=2, default=str))

    # ------------------------------------------------------------------
    # System commands
    # ------------------------------------------------------------------

    def _cmd_stats(self, args: List[str]) -> None:
        info = self.kernel.syscall("kernel_stats")
        width = max(len(k) for k in info)
        for k, v in info.items():
            print(f"  {k:<{width}} : {v}")

    def _cmd_history(self, args: List[str]) -> None:
        for i, cmd in enumerate(self._history[-20:], 1):
            print(f"  {i:>3}  {cmd}")

    def _cmd_help(self, args: List[str]) -> None:
        sections = {
            "Memory": [
                ("mem",      "list all keys in memory"),
                ("remember", "<key> <value> [--persist]  store a value"),
                ("recall",   "<key>                       retrieve a value"),
                ("forget",   "<key>                       delete a key"),
            ],
            "Filesystem": [
                ("ls",    "[path]          list directory"),
                ("cat",   "<path>          read a file"),
                ("write", "<path> <text>   create/overwrite a file"),
                ("rm",    "<path>          delete a file"),
                ("cd",    "[path]          change directory"),
                ("pwd",   "                show current directory"),
            ],
            "Processes": [
                ("ps",    "[status]        list processes"),
                ("spawn", "<name> [msg]    create and queue a process"),
                ("kill",  "<pid>           terminate a process"),
            ],
            "Scheduler": [
                ("sched", "show scheduler status and recent log"),
            ],
            "System": [
                ("stats",   "kernel statistics"),
                ("history", "command history"),
                ("help",    "this message"),
                ("exit",    "shutdown and quit"),
            ],
        }
        for section, cmds in sections.items():
            print(f"\n  [{section}]")
            for name, desc in cmds:
                print(f"    {name:<12} {desc}")
        print()

    def _cmd_exit(self, args: List[str]) -> None:
        self.kernel.shutdown()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return self._cwd.rstrip("/") + "/" + path
