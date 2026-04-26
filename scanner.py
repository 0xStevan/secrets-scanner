"""Secrets Scanner — recursively scans a directory for hardcoded secrets.

Built by 0xStevan. v0 — regex-based detection of common secret types.
"""

import argparse
import sys
from pathlib import Path

from patterns import PATTERNS

# Directories we never want to scan — they contain dependencies / metadata,
# not your code. Real scanners load this from a config file; v0 hardcodes it.
SKIP_DIRS = {"venv", "__pycache__", "node_modules", ".git", ".idea", ".vscode"}


def scan_file(file_path: Path) -> list[dict]:
    """Scan a single file line by line. Return a list of findings."""
    findings = []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                for pattern_name, regex in PATTERNS:
                    match = regex.search(line)
                    if match:
                        findings.append({
                            "file": str(file_path),
                            "line": line_number,
                            "pattern": pattern_name,
                            "match": match.group(0),
                        })
    except (UnicodeDecodeError, PermissionError):
        # Binary file or unreadable — silently skip. v0 behavior.
        pass
    return findings


def scan_directory(root: Path) -> list[dict]:
    """Recursively scan every text file under `root`. Return all findings."""
    all_findings = []
    for path in root.rglob("*"):
        # Skip directories themselves — we only scan files.
        if not path.is_file():
            continue
        # Skip if any parent directory is in our skip list.
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        all_findings.extend(scan_file(path))
    return all_findings


def print_findings(findings: list[dict]) -> None:
    """Print findings in a human-readable format."""
    if not findings:
        print("No secrets found.")
        return

    print(f"Found {len(findings)} potential secret(s):\n")
    for f in findings:
        print(f"  [{f['pattern']}]")
        print(f"    {f['file']}:{f['line']}")
        print(f"    {f['match']}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan a directory for hardcoded secrets (API keys, tokens, private keys).",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Directory to scan recursively.",
    )
    args = parser.parse_args()

    if not args.path.is_dir():
        print(f"Error: {args.path} is not a directory.", file=sys.stderr)
        return 2

    findings = scan_directory(args.path)
    print_findings(findings)

    # Exit code 1 if anything was found — lets CI/CD pipelines fail the build.
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
