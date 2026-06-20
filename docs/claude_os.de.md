[English](./claude_os.md) | [简体中文](./claude_os.zh-CN.md) | [Deutsch](./claude_os.de.md) · [← Zurück](../README.md)

# ClaudeOS

Ein minimales, KI-natives Betriebssystem, implementiert in reinem Python — ohne externe Abhängigkeiten.  
ClaudeOS stellt eine Unix-inspirierte Shell auf einem winzigen Kernel bereit, der Speicher, Prozesse, ein virtuelles Dateisystem, einen Cron-Scheduler, einen In-Memory-Tresor für Secrets sowie benannte Hintergrund-Agenten (Coworkers) verwaltet.

## Architektur

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

### Komponenten

| Komponente | Datei | Zweck |
|------------|-------|-------|
| Kernel | `claude_os/kernel.py` | Syscall-Tabelle, Verdrahtung der Subsysteme, Boot/Shutdown |
| MemoryBus | `claude_os/memory.py` | Zweistufiger Key-Value-Speicher (flüchtig + persistiertes JSON) |
| VirtualFS | `claude_os/fs.py` | In-Memory-Dateisystem im POSIX-Stil |
| ProcessTable | `claude_os/process.py` | Leichtgewichtiges, kooperatives Prozessmodell |
| Scheduler | `claude_os/scheduler.py` | FIFO-Queue mit Hintergrund-Daemon-Thread |
| CronDaemon | `claude_os/cron.py` | Intervallbasierter Scheduler für Hintergrund-Tasks |
| SecretVault | `claude_os/secrets.py` | Thread-sicherer In-Memory-Speicher für Zugangsdaten |
| CoworkerRegistry | `claude_os/coworker.py` | Benannte Hintergrund-Agenten mit Secret-Injection |
| Shell | `claude_os/shell.py` | Interaktive REPL mit Unix-artigen Befehlen |

## Installation

Keine Abhängigkeiten — benötigt Python 3.9+.

```bash
git clone https://github.com/horstducker/awesome-deepseek-agent.git
cd awesome-deepseek-agent
python run_os.py
```

## Einstiegspunkte

| Skript | Beschreibung |
|--------|--------------|
| `python run_os.py` | Interaktive Shell (REPL) |
| `python web_dashboard.py` | Live-Web-Dashboard unter `http://localhost:8080` |
| `python dashboard.py` | ANSI-Terminal-Dashboard (1 s Refresh) |
| `python snes_os.py` | Secret-of-Mana-Edition — 8 Elementar-Coworker, SNES-TUI |
| `python run_cron.py` | Headless-CI-Modus — lädt Secrets aus der Umgebung, feuert alle Coworker |

## Schnellstart

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

## Shell-Befehle

### Speicher (Memory)
| Befehl | Beschreibung |
|--------|--------------|
| `mem` | Alle aktuell im Speicher liegenden Schlüssel auflisten |
| `remember <key> <value> [--persist]` | Wert speichern; `--persist` übersteht Neustarts |
| `recall <key>` | Gespeicherten Wert abrufen |
| `forget <key>` | Schlüssel aus dem Speicher löschen (meldet `not found`, falls nicht vorhanden) |

Intern werden diese auf Memory-Syscalls abgebildet: `mem_read`, `mem_write`, `mem_delete` und `mem_list`. `forget` läuft über `mem_delete`, das `True` zurückgibt, wenn ein Schlüssel entfernt wurde, und `False`, wenn er nicht existierte — so bleibt jede Löschung über die Syscall-Tabelle auditierbar.

### Dateisystem (Filesystem)
| Befehl | Beschreibung |
|--------|--------------|
| `ls [path]` | Verzeichnisinhalt auflisten |
| `cat <path>` | Dateiinhalt ausgeben |
| `write <path> <text>` | Datei erstellen oder überschreiben |
| `rm <path>` | Datei löschen |
| `cd [path]` | Arbeitsverzeichnis wechseln |
| `pwd` | Arbeitsverzeichnis ausgeben |

### Prozesse (Processes)
| Befehl | Beschreibung |
|--------|--------------|
| `ps [status]` | Prozesse auflisten (optional nach Status filtern) |
| `spawn <name> [msg]` | Hintergrundprozess erstellen und einreihen |
| `kill <pid>` | Prozess beenden |

### Cron-Scheduler
| Befehl | Beschreibung |
|--------|--------------|
| `cron list` | Alle geplanten Jobs auflisten |
| `cron add <name> <interval> <command…>` | Einen Shell-Befehl in einem Intervall einplanen (z. B. `cron add heartbeat 10s write /var/log/hb.txt tick`) |
| `cron log [n]` | Letzte n Auslöse-Ereignisse anzeigen (Standard 10) |
| `cron enable <id>` | Job aktivieren |
| `cron disable <id>` | Job deaktivieren |
| `cron run <id>` | Job sofort auslösen |
| `cron remove <id>` | Job entfernen (Alias: `cron rm <id>`) |

Intervall-Formate: `30s`, `5m`, `2h`, `1d`. Der eingeplante Befehl ist ein beliebiger eingebauter Shell-Befehl; er wird vom Cron-Daemon erneut ausgeführt, sobald das Intervall abläuft. `secret` und `coworker` akzeptieren `rm` ebenfalls als Alias für `delete`/`remove`.

### Secrets
| Befehl | Beschreibung |
|--------|--------------|
| `secret list` | Secret-Namen auflisten (Werte werden nie angezeigt) |
| `secret set <NAME> <VALUE>` | Ein Secret im Speicher ablegen |
| `secret get <NAME>` | Vorhandensein bestätigen — gibt immer `***` aus |
| `secret delete <NAME>` | Ein Secret entfernen |
| `secret env` | Secrets aus Umgebungsvariablen laden, die zu `*_API_KEY` oder `CLAUDE_SECRET_*` passen |

Secret-Werte werden **niemals** auf die Festplatte geschrieben, niemals ausgegeben und tauchen niemals in der Befehlshistorie auf.

### Coworkers
| Befehl | Beschreibung |
|--------|--------------|
| `coworker list` | Alle registrierten Coworker auflisten |
| `coworker add <NAME> <SCHEDULE> [SECRETS…]` | Einen Demo-Coworker registrieren |
| `coworker remove <NAME>` | Einen Coworker abmelden |
| `coworker fire <NAME>` | Sofort ausführen |
| `coworker enable <NAME>` | Aktivieren |
| `coworker disable <NAME>` | Deaktivieren |

### System
| Befehl | Beschreibung |
|--------|--------------|
| `sched` | Scheduler-Status und jüngstes Log anzeigen |
| `stats` | Kernel-Statistiken |
| `history` | Befehlshistorie |
| `exit` / `quit` | Herunterfahren und beenden |

## Secret-of-Mana-Edition

`snes_os.py` ist eine eigenständige 16-Bit-SNES-artige Terminal-Oberfläche, die 8 unabhängige Elementar-Coworker betreibt — inspiriert von den Mana-Geistern aus *Secret of Mana*.

```bash
python snes_os.py
```

Steuerung: `1-8` Geist auswählen · `F` sofort auslösen · `E` aktivieren · `D` deaktivieren · `Q` beenden

### Die 8 Mana-Geister

| # | Geist | Element | Intervall | Aktion |
|---|-------|---------|-----------|--------|
| 1 | Undine | Wasser | 8s | Zählt Memory-Schlüssel |
| 2 | Gnome | Erde | 12s | Schreibt ins virtuelle Dateisystem |
| 3 | Sylphid | Wind | 5s | Schnellster Läufer, Böen-Zähler |
| 4 | Salamando | Feuer | 10s | Pulst Kernel-Syscall-Statistiken |
| 5 | Lumina | Licht | 20s | Prüft die Integrität des Secret-Tresors |
| 6 | Shade | Dunkelheit | 15s | Durchsucht das Auslöse-Log nach Fehlern |
| 7 | Luna | Mond | 30s | Heartbeat- & Uptime-Tracker |
| 8 | Dryad | Holz | 25s | Memory-Statistiken & Aufräumen |

Jeder Geist läuft nach seinem eigenen Intervall, vollständig unabhängig von den anderen. Die Anzeige zeigt ein 2×4-Raster aus Geist-Karten mit HP-Balken-artigen Lauf-Zählern und einem Live-Auslöse-Log.

## Web-Dashboard

```bash
python web_dashboard.py          # serves on http://localhost:8080
python web_dashboard.py --port 9090
python web_dashboard.py --quiet  # no demo jobs
```

Das Dashboard pollt jede Sekunde `/api/state` und zeigt Kernel-Statistiken, Secrets (maskiert), Speicher, Cron-Jobs, Coworker und das Auslöse-Log — alles in einer browserbasierten UI im Dark-Theme.

## DeepSeek-Modellkonfiguration

ClaudeOS selbst ist abhängigkeitsfrei und ruft kein Modell auf, doch seine Coworker und die Headless-Cron-Läufe sind darauf ausgelegt, über ihre Secret-injizierten Aktionen [DeepSeek](https://platform.deepseek.com/)-Modelle anzusteuern. Wenn du einen Coworker an die DeepSeek-API anbindest, gelten die folgenden Parameter (Preise in USD pro 1 Mio. Tokens, Stand Juni 2026 — aktuelle Tarife auf der [Preisseite](https://api-docs.deepseek.com/quick_start/pricing) prüfen):

| Modell | Kontext | Max. Output | Input (Cache-Miss) | Input (Cache-Hit) | Output |
|--------|--------:|------------:|-------------------:|------------------:|-------:|
| **DeepSeek-V4-Pro** | 1.048.576 (1M) | 384.000 | $1,74 | ~$0,174 | $3,48 |
| **DeepSeek-V4-Flash** | 1.048.576 (1M) | 384.000 | $0,14 | ~$0,014 | $0,28 |

- **1M-Kontext** (`context_length: 1000000`) ist seit dem V4-Release der Standard über alle offiziellen DeepSeek-Dienste hinweg.
- **Thinking-/Reasoning-Modus** wird unterstützt und ist standardmäßig aktiv (wird als Output abgerechnet). Über das OpenAI-kompatible SDK schaltest du ihn mit `extra_body={"thinking": {"type": "enabled"}}` um und steuerst die Tiefe über `reasoning_effort` (`"high"` oder `"xhigh"` für maximales Reasoning). Die Gedankenkette wird als `reasoning_content` zurückgegeben, auf derselben Ebene wie `content` (im Stream als `delta.reasoning_content`). Mit Reasoning inkompatible Sampling-Parameter werden automatisch aus dem Request entfernt.
- Die alten Modellnamen `deepseek-chat` / `deepseek-reasoner` werden ab dem 2026-07-24 zugunsten der V4-Modellfamilie eingestellt.

Lege den Schlüssel als Secret ab (`secret set DEEPSEEK_API_KEY …` oder `secret env`) und deklariere ihn am Coworker, damit die Registry ihn erst zur Aufrufzeit injiziert:

```
claude@os:~$ secret set DEEPSEEK_API_KEY sk-...
claude@os:~$ coworker add reporter 1h DEEPSEEK_API_KEY
```

## GitHub Actions / Headless CI

`run_cron.py` ist der Headless-Einstiegspunkt für geplante CI-Läufe:

```bash
DEEPSEEK_API_KEY=sk-... python run_cron.py
```

Der mitgelieferte Workflow `.github/workflows/cron-worker.yml` läuft täglich um 08:00 UTC und unterstützt `workflow_dispatch`. Er injiziert `DEEPSEEK_API_KEY`, `OPENAI_API_KEY` und `ANTHROPIC_API_KEY` aus den Repository-Secrets.

## ClaudeOS erweitern

### Einen eigenen Syscall registrieren

```python
from claude_os import Kernel, Shell

kernel = Kernel()
kernel.boot()

kernel.register_syscall("greet", lambda name: f"Hello, {name}!")

shell = Shell(kernel)
shell.run()
```

### Einen Coworker programmatisch registrieren

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

## Tests ausführen

```bash
python -m claude_os.tests
```

## Designentscheidungen

- **Reines Python, null Abhängigkeiten** — läuft überall, wo Python 3.9+ verfügbar ist.
- **Kooperatives Multitasking** — Prozesse geben von sich aus ab; keine Verdrängung (Preemption).
- **Zweistufiger Speicher** — kurzfristig (dict) für flüchtigen Zustand, langfristig (JSON-Datei) für Persistenz. Secrets liegen ausschließlich in der kurzfristigen Stufe und werden nie ins JSON geschrieben.
- **Syscall-Tabelle** — alle Befehle laufen über `kernel.syscall()`, wodurch jede Aktion auditierbar und erweiterbar wird.
- **Secret-Isolation** — `SecretVault` ist thread-sicher; Werte werden überall als `***` maskiert, auch im Cron-Auslöse-Log und in der Befehlshistorie.
- **Coworker statt nacktem Cron** — Coworker deklarieren ihre Secret-Abhängigkeiten explizit; die Registry löst sie zur Aufrufzeit auf, niemals zur Registrierungszeit.

*Erstellt von Grille mit Claude Code*
