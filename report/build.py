"""Print report/report.html to report/forager-report.pdf with headless Google Chrome and check the page limit.

The main body (everything before the appendix) must fit in six A4 pages; the appendix holds figures and
supplementary tables. The report is printed twice: once in full, and once with ?main, which drops the
appendix, to count the main body's pages.

Run: .venv/bin/python report/build.py
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report.html"
OUT = ROOT / "forager-report.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MAX_MAIN_PAGES = 6


def print_pdf(url: str, out: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="forager-report-") as profile:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                        "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                        "--virtual-time-budget=8000", f"--print-to-pdf={out}", url],
                       check=True, capture_output=True, timeout=120)
    return len(re.findall(rb"/Type\s*/Page(?!s)", out.read_bytes()))


def main() -> int:
    url = SOURCE.as_uri()
    pages = print_pdf(url, OUT)
    with tempfile.TemporaryDirectory() as tmp:
        main_pages = print_pdf(url + "?main", Path(tmp) / "main.pdf")
    print(f"{OUT.relative_to(ROOT.parent)}: {pages} pages (main body {main_pages}, appendix {pages - main_pages})")
    if main_pages > MAX_MAIN_PAGES:
        print(f"the main body is over {MAX_MAIN_PAGES} pages")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
