"""Console script entry point."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path


def test_command_points_at_main() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["pushit"] == "lupaxa.pushit.cli:main"


def test_python_m_module_requires_a_mode() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": "src"}
    result = subprocess.run(
        [sys.executable, "-m", "lupaxa.pushit"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "--text" in result.stderr
