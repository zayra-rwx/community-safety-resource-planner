"""Validate the current compact report block; historical full check is check_metric.py."""
from pathlib import Path
import contextlib
import io
import re
import textwrap

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
report = (ROOT / "my-audit.md").read_text(encoding="utf-8")
code = textwrap.dedent(re.search(r"```python\n(.*?)\n\s*```", report, re.S).group(1))
assert code.strip() == (HERE / "score_check.py").read_text(encoding="utf-8").strip()
output = io.StringIO()
with contextlib.redirect_stdout(output):
    exec(compile(code, "<compact report check>", "exec"), {"__name__": "__main__"})
result = "Targeted compact ranking check only; no new full-data recomputation.\n" + output.getvalue()
(HERE / "compact-output.txt").write_text(result, encoding="utf-8")
print(result)
