"""Validate the concise submission and unchanged audited implementation."""
from pathlib import Path
import json
import subprocess
import re
import textwrap
import mistune

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
lines = []
def record(s):
    print(s)
    lines.append(s)
def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
assert git("branch", "--show-current") == "Olga"
assert git("rev-parse", "main") == "058dee6211e15bd6f079fb22a35151b133b3e611"
v = json.loads((OUT / "version.json").read_text())
for name, blob in v["tracked_git_blobs"].items():
    assert git("hash-object", name) == blob, name
record("PASS: Olga branch; main unchanged; 20 baseline file identities preserved")
report = (ROOT / "my-audit.md").read_text(encoding="utf-8")
shared = (ROOT / "change-requests.md").read_text(encoding="utf-8")
assert re.findall(r"^## .*$", report, re.M) == ["## Context", "## 1. Feature audit", "## 2. Number audit", "## My contribution"]
assert "AUDIT-01" in report and "AUDIT-01" in shared
assert "OLGA-001" not in report and "OLGA-001" not in shared
for h in ["# Team change requests", "## Claims", "## Requests", "## Follow through"]:
    assert h in shared
assert "Status: proposed; not implemented" in shared
assert "Olga Tovstogan" in shared
code = textwrap.dedent(re.search(r"```python\n(.*?)\n\s*```", report, re.S).group(1))
assert code.strip() == (OUT / "score_check.py").read_text(encoding="utf-8").strip()
for path in [ROOT / "my-audit.md", ROOT / "change-requests.md", *OUT.glob("*.md")]:
    text = path.read_text(encoding="utf-8")
    assert text.count("```") % 2 == 0
    assert mistune.create_markdown(renderer="ast", plugins=["table"])(text)
    assert all(line.rstrip() == line for line in text.splitlines()), path
for filename in ["feature-output.txt", "numeric-output.txt", "numeric_results.json", "test-output.txt", "compact-output.txt", "official-change-requests-template.md"]:
    assert (OUT / filename).is_file()
record("PASS: concise headings, shared official structure, attribution, matching request ID, code extraction, Markdown and evidence paths")
record("NEW: compact ranking check passed (see compact-output.txt); no new full-data recomputation or test-suite run")
record("HISTORICAL: full-data comparison matched all 1172 districts; baseline tests 40 passed in 4.14s")
record("Scope: submitted CLI only; AUDIT-01 proposed, not implemented; no numeric defect requested")
(OUT / "validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
