# secrets-scanner

A Python CLI that scans a directory for hardcoded secrets — API keys, AWS credentials, GitHub tokens, private keys, and more.

Built by [0xStevan](https://github.com/0xStevan) as part of the journey toward AppSec Engineer.

---

## The problem

Hardcoded secrets in source code are one of the most common — and most damaging — security failures in modern software. A single committed AWS key can lead to a compromised cloud account in under 60 seconds (bots scrape public GitHub commits in real time). Internal codebases are no safer: developers leave credentials in `.env` files, config samples, test fixtures, and old branches all the time.

This tool catches them before they ship.

## What it does

- Recursively walks a directory tree
- Reads each text file line-by-line
- Matches every line against 8 regex patterns covering common secret types
- Reports findings with file path, line number, pattern name, and the matched substring
- Returns a non-zero exit code when secrets are found, so CI/CD pipelines can fail builds containing leaked credentials

## What it detects (v0)

| Type | Example |
|---|---|
| AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| AWS Secret Access Key | `aws_secret_access_key = "..."` (40 chars) |
| GitHub Personal Access Token | `ghp_...` (40 chars) |
| GitHub OAuth Token | `gho_...` (40 chars) |
| Slack Token | `xoxb-...`, `xoxp-...`, etc. |
| Private Key Header | `-----BEGIN RSA/OPENSSH/EC PRIVATE KEY-----` |
| Generic API Key | `api_key = "..."` (20+ chars) |
| Generic Secret / Password | `secret = "..."` / `password = "..."` (8+ chars) |

Two strategies are mixed:
- **Prefix-based patterns** match the secret's own format (e.g. `AKIA` + 16 chars). Near-zero false positives.
- **Context-required patterns** require a variable name like `api_key` or `secret` next to a long quoted string. Cuts false positives on hashes, UUIDs, and random IDs.

## Installation

```bash
git clone https://github.com/0xStevan/secrets-scanner.git
cd secrets-scanner
```

No dependencies — uses only the Python standard library. Requires Python 3.9+.

## Usage

```bash
python3 scanner.py /path/to/scan
```

Example:

```bash
$ python3 scanner.py ./tests
Found 6 potential secret(s):

  [AWS Access Key ID]
    tests/sample_secrets.txt:13
    AKIAIOSFODNN7EXAMPLE

  [GitHub Personal Access Token]
    tests/sample_secrets.txt:19
    ghp_1234567890abcdefghijklmnopqrstuvwxyz
  ...
```

Exit codes:
- `0` — no secrets found
- `1` — secrets found
- `2` — invalid path argument

## Skipped directories

The scanner ignores `venv/`, `__pycache__/`, `node_modules/`, `.git/`, `.idea/`, and `.vscode/` to avoid noise from dependencies and metadata.

## Known limitations (v0)

This is v0 — deliberately minimal. Things it does **not** do yet:
- No entropy detection (random-looking strings without surrounding context get missed)
- No allowlist support (false positives can't be silenced per-line)
- No JSON / SARIF output (human-readable text only)
- No Git history scanning (only the working tree)
- No multi-line secret detection (private keys are matched by header line only)
- Patterns can overlap (one secret may produce multiple findings)
- Pattern list is hardcoded, not configurable

## Roadmap

- **v0.2** — Entropy detection (catch random-looking secrets without context clues)
- **v0.3** — Allowlist file (`.secretsignore`) + JSON/SARIF output
- **v0.4** — Git history scanning (walk every commit, not just current files)
- **v1.0** — Packaged as a [GitHub Action](https://github.com/marketplace?type=actions) for drop-in CI/CD use

## Why this exists

This project is part of a public learning journey toward AppSec Engineer. Real tools like [TruffleHog](https://github.com/trufflesecurity/trufflehog), [GitGuardian](https://www.gitguardian.com/), and [Gitleaks](https://github.com/gitleaks/gitleaks) solve this problem at scale — but building one from scratch teaches the pattern design, false-positive tradeoffs, and CI integration realities that no tutorial can.

Follow the journey: [github.com/0xStevan](https://github.com/0xStevan)

## License

MIT
