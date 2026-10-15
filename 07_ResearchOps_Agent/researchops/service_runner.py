"""Run a service with bounded, redacted stdout/stderr and signal forwarding."""

import argparse
import logging
import os
import signal
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from researchops.core.security import redact_sensitive_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not Path(command[0]).is_absolute():
        parser.error("Service executable must be an absolute path")
    os.umask(0o077)
    args.log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        args.log, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("service.output")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    child = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )

    def forward(signum, _frame):
        if child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    try:
        # Bounded reads also prevent a single malicious line allocating unbounded memory.
        while True:
            line = child.stdout.readline(65536)
            if not line:
                break
            logger.info("%s", redact_sensitive_text(line.rstrip()))
        returncode = child.wait()
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        handler.close()
    sys.exit(returncode if returncode >= 0 else 128 - returncode)


if __name__ == "__main__":
    main()
