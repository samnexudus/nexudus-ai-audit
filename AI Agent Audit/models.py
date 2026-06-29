"""
Shared data types and the nexudus CLI helper.
"""

import json
import os
import subprocess
from dataclasses import dataclass, field

# Ensure the dotnet tools directory is on PATH so nexudus is always found
_dotnet_tools = os.path.expanduser("~/.dotnet/tools")
if _dotnet_tools not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _dotnet_tools + os.pathsep + os.environ.get("PATH", "")


@dataclass
class CheckResult:
    name:   str
    status: str          # "pass" | "warn" | "fail" | "skip"
    detail: str = ""
    hint:   str = ""


@dataclass
class Section:
    title:   str
    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult):
        self.results.append(result)

    @property
    def score(self) -> dict:
        counts = {"pass": 0, "warn": 0, "fail": 0, "skip": 0}
        for r in self.results:
            counts[r.status] += 1
        return counts


def nexudus(args: list[str]) -> dict:
    """Run a nexudus CLI command and return the parsed JSON envelope."""
    cmd = ["nexudus"] + args + ["--agent"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "data": None, "summary": result.stderr.strip() or "No output"}
