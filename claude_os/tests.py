"""
Smoke tests for ClaudeOS subsystems.
Run with: python -m claude_os.tests
"""

from __future__ import annotations

import time
import sys


def run_tests() -> None:
    passed = 0
    failed = 0

    def ok(name: str) -> None:
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name: str, reason: str) -> None:
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}: {reason}")

    print("\n=== ClaudeOS smoke tests ===\n")

    # ------------------------------------------------------------------
    # MemoryBus
    # ------------------------------------------------------------------
    from claude_os.memory import MemoryBus
    m = MemoryBus()
    m.init()

    m.write("x", 42)
    assert m.read("x") == 42, "read after write"
    ok("memory: basic write/read")

    m.write("y", "hello", persist=False)
    keys = m.list_keys()
    assert "x" in keys and "y" in keys
    ok("memory: list_keys")

    m.delete("x")
    assert m.read("x") is None
    ok("memory: delete")

    # ------------------------------------------------------------------
    # VirtualFS
    # ------------------------------------------------------------------
    from claude_os.fs import VirtualFS
    fs = VirtualFS()
    fs.init()

    fs.write("/tmp/test.txt", "hello world")
    assert fs.read("/tmp/test.txt") == "hello world"
    ok("fs: write/read")

    fs.write("/tmp/test.txt", " more", mode="a")
    assert fs.read("/tmp/test.txt") == "hello world more"
    ok("fs: append mode")

    listing = fs.list_dir("/tmp")
    names = [e["name"] for e in listing]
    assert "test.txt" in names
    ok("fs: list_dir")

    fs.delete("/tmp/test.txt")
    assert fs.read("/tmp/test.txt") is None
    ok("fs: delete")

    # ------------------------------------------------------------------
    # ProcessTable
    # ------------------------------------------------------------------
    from claude_os.process import ProcessTable, Status
    pt = ProcessTable()

    result_holder = []
    pid = pt.spawn("test-task", lambda: result_holder.append(99))
    proc = pt.get(pid)
    assert proc is not None and proc.status == Status.READY
    ok("process: spawn")

    proc.run()
    assert proc.status == Status.DONE and result_holder == [99]
    ok("process: run to completion")

    pid2 = pt.spawn("killable", lambda: None)
    pt.kill(pid2)
    assert pt.get(pid2).status == Status.ZOMBIE
    ok("process: kill → zombie")

    reaped = pt.reap_zombies()
    assert reaped == 1 and pt.get(pid2) is None
    ok("process: reap zombies")

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------
    from claude_os.scheduler import Scheduler
    pt2 = ProcessTable()
    sched = Scheduler(pt2)
    sched.start()

    done = []
    pid3 = pt2.spawn("sched-task", lambda: done.append(1))
    queued = sched.enqueue(pid3)
    assert queued
    ok("scheduler: enqueue")

    time.sleep(0.3)
    assert done == [1], f"task not executed, done={done}"
    ok("scheduler: task executed")

    sched.stop()

    # ------------------------------------------------------------------
    # Kernel
    # ------------------------------------------------------------------
    from claude_os.kernel import Kernel
    k = Kernel()
    k.boot()

    k.syscall("mem_write", "greeting", "hello")
    assert k.syscall("mem_read", "greeting") == "hello"
    ok("kernel: mem syscalls")

    k.syscall("fs_write", "/tmp/k.txt", "kernel test")
    assert k.syscall("fs_read", "/tmp/k.txt") == "kernel test"
    ok("kernel: fs syscalls")

    stats = k.syscall("kernel_stats")
    assert stats["version"] == "0.1.0"
    ok("kernel: stats syscall")

    k.shutdown()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total = passed + failed
    print(f"\n  {passed}/{total} passed", "✓" if failed == 0 else "✗")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
