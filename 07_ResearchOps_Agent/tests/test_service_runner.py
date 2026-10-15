"""Operational templates and bounded logging verified without touching launchd."""

import plistlib
import subprocess
import sys
from pathlib import Path


def test_service_templates_are_non_root_and_explicit():
    for filename in ["com.researchops.agent.plist", "com.cloudflare.cloudflared.plist"]:
        config = plistlib.loads((Path("deploy/macos") / filename).read_bytes())
        assert config["UserName"] == "lanting"
        assert config["KeepAlive"] is True
        assert config["WorkingDirectory"].endswith("researchops-agent")
        assert "researchops.service_runner" in config["ProgramArguments"]
        if "cloudflare" in filename:
            args = config["ProgramArguments"]
            assert args[args.index("--config") + 1] == "/etc/cloudflared/config.yml"
            assert args[-2:] == ["run", "1be9a224-0f36-4d38-87a9-890024dd4e3e"]
        else:
            assert config["EnvironmentVariables"]["API_HOST"] == "127.0.0.1"


def test_runner_redacts_and_rotates_output(tmp_path):
    log = tmp_path / "logs" / "test.log"
    code = "print('invitation_code=synthetic-secret'); [print('x'*65500) for _ in range(170)]"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "researchops.service_runner",
            "--log",
            str(log),
            "--",
            sys.executable,
            "-c",
            code,
        ],
        timeout=15,
        capture_output=True,
    )
    assert result.returncode == 0
    paths = list(log.parent.glob("test.log*"))
    assert len(paths) == 2
    assert all(path.stat().st_size <= 10 * 1024 * 1024 for path in paths)
    assert all(b"synthetic-secret" not in path.read_bytes() for path in paths)
