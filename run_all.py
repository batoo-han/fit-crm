"""Launch API, frontend dev server and Telegram bot together."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional


IS_WINDOWS = os.name == "nt"


@dataclass
class Service:
    name: str
    command: str
    cwd: Optional[str] = None
    process: subprocess.Popen | None = None


SERVICES: list[Service] = [
    Service(
        name="CRM API",
        command=f"{sys.executable} run_crm_api.py",
        cwd=None,
    ),
    Service(
        name="Frontend (Vite)",
        command="npm run dev -- --host",
        cwd="crm-frontend",
    ),
    Service(
        name="Telegram Bot",
        command=f"{sys.executable} bot.py",
        cwd=None,
    ),
]


def start_service(service: Service) -> None:
    env = os.environ.copy()
    print(f"[launcher] Starting {service.name} → {service.command}")
    service.process = subprocess.Popen(
        service.command,
        cwd=service.cwd or os.getcwd(),
        env=env,
        shell=True if IS_WINDOWS else False,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
    )


def stop_service(service: Service) -> None:
    proc = service.process
    if not proc or proc.poll() is not None:
        return
    print(f"[launcher] Stopping {service.name}")
    try:
        if IS_WINDOWS:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            time.sleep(0.5)
            proc.terminate()
        else:
            proc.terminate()
    except Exception:
        pass
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


def main() -> int:
    try:
        for service in SERVICES:
            start_service(service)

        print("[launcher] All services started. Press Ctrl+C to stop.")

        while True:
            time.sleep(1)
            for service in SERVICES:
                proc = service.process
                if proc and proc.poll() is not None:
                    print(
                        f"[launcher] {service.name} exited with code {proc.returncode}"
                    )
                    return proc.returncode or 0
    except KeyboardInterrupt:
        print("\n[launcher] Stopping services…")
        return 0
    finally:
        for service in SERVICES:
            stop_service(service)


if __name__ == "__main__":
    sys.exit(main())


