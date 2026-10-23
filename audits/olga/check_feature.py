"""Exercise the committed CLI in subprocesses; no dashboard imports."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def run(args):
    result = subprocess.run([sys.executable, '-m', 'src.analysis', *args], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    print('COMMAND: .venv/Scripts/python.exe -m src.analysis ' + ' '.join(args))
    print('EXIT:', result.returncode)
    print(result.stdout.rstrip())
    return result.stdout


normal = run(['--top', '3'])
assert '0182' in normal and '87.679181' in normal
assert normal.index('0182') < normal.index('1494') < normal.index('0636')
empty = run(['--start', '2027-01-01', '--end', '2027-01-31', '--top', '3'])
assert 'Empty DataFrame' in empty
reversed_dates = run(['--start', '2026-09-19', '--end', '2025-01-01', '--top', '3'])
assert 'Empty DataFrame' in reversed_dates
repeat = run(['--top', '3'])
assert repeat == normal
help_text = run(['--help'])
assert '--start' in help_text and '--end' in help_text and '--top' in help_text
print('NORMAL / EMPTY / REVERSED / REPEAT / HELP ASSERTIONS PASSED')
print('Observed interface: terminal text only. No browser interactions were performed.')
