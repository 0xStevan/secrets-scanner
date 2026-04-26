"""Regex patterns for known secret types.

Each pattern is a tuple of (display_name, compiled_regex). Adding a new
secret type means adding a new entry here — no changes to scanner.py needed.

Two strategies are mixed below:
  - Prefix-based: the secret's own format is distinctive (AKIA..., ghp_..., xox...).
    High confidence, very few false positives.
  - Context-required: pattern requires a variable name like `api_key` or `secret`
    next to a long string. Cuts false positives on generic-looking hashes/UUIDs.
"""

import re

PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    (
        "GitHub Personal Access Token",
        re.compile(r"ghp_[A-Za-z0-9]{36}"),
    ),
    (
        "GitHub OAuth Access Token",
        re.compile(r"gho_[A-Za-z0-9]{36}"),
    ),
    (
        "Slack Token",
        re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"),
    ),
    (
        "Private Key Header",
        re.compile(r"-----BEGIN (RSA |OPENSSH |DSA |EC |PGP )?PRIVATE KEY-----"),
    ),
    (
        "Generic API Key (context-required)",
        re.compile(
            r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]"
        ),
    ),
    (
        "Generic Secret (context-required)",
        re.compile(
            r"(?i)(secret|password|passwd)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
        ),
    ),
    (
        "AWS Secret Key (context-required)",
        re.compile(
            r"(?i)aws[_-]?(secret[_-]?)?(access[_-]?)?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]"
        ),
    ),
]
