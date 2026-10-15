"""Read-only deployment template/installation checks. Never installs or restarts."""

import argparse
import json
import plistlib
import stat
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--installed", action="store_true", help="同时检查已安装文件，不读取凭证内容"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = {}
    for name in ["com.researchops.agent.plist", "com.cloudflare.cloudflared.plist"]:
        config = plistlib.loads((root / "deploy/macos" / name).read_bytes())
        report[name] = config["UserName"] == "lanting" and config["KeepAlive"] is True
        if not report[name]:
            raise SystemExit("Unsafe service template")
    result = subprocess.run(
        [
            "/opt/homebrew/bin/cloudflared",
            "tunnel",
            "--config",
            str(root / "deploy/macos/cloudflared.config.yml"),
            "ingress",
            "validate",
        ],
        capture_output=True,
        timeout=15,
    )
    report["ingress_valid"] = result.returncode == 0
    if args.installed:
        for name in ["config.yml", "1be9a224-0f36-4d38-87a9-890024dd4e3e.json"]:
            path = Path("/etc/cloudflared") / name
            try:
                info = path.lstat()
                report["installed_" + name] = (
                    stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
                )
            except OSError:
                report["installed_" + name] = False
    print(json.dumps(report, indent=2))
    if not all(report.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
