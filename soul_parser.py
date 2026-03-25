"""
soul_parser.py — Flexible Soul YAML Loader

Loads any soul YAML regardless of schema version or structure.
Auto-corrects minor formatting issues.
Extracts identity information.
Flattens the entire tree into a rich system prompt any model can use.

Part of the Soul Room framework.
"""

import os
import re
import yaml


# ── Flexible Name Extraction ───────────────────────────
# Walk common paths to find a display name no matter the schema variant.
_NAME_PATHS = [
    ("identity", "designation"),
    ("identity", "name"),
    ("persona", "name"),
    ("persona", "designation"),
    ("character", "name"),
    ("name",),
    ("designation",),
]


def extract_name(soul: dict, fallback: str = "Unknown") -> str:
    """Pull a display name from whichever field the YAML uses."""
    if not isinstance(soul, dict):
        return fallback
    for path in _NAME_PATHS:
        node = soul
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                node = None
                break
        if isinstance(node, str) and node.strip():
            return node.strip()
    return fallback


def extract_field(soul: dict, *paths, fallback=None):
    """
    Extract a value from the soul dict by trying multiple paths.
    
    Usage:
        extract_field(soul, ("identity", "soul_type"), ("persona", "type"), fallback="general")
    """
    if not isinstance(soul, dict):
        return fallback
    for path in paths:
        if isinstance(path, str):
            path = (path,)
        node = soul
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                node = None
                break
        if node is not None:
            return node
    return fallback


# ── YAML Auto-Repair ──────────────────────────────────
def _attempt_repair(raw: str) -> str:
    """
    Best-effort repair of common YAML typos:
    - tabs → spaces
    - trailing commas inside braces
    - Python-style triple-quoted blocks → YAML block scalar
    - unbalanced quotes
    """
    # Tabs to 2-space indent
    raw = raw.replace("\t", "  ")
    # Trailing commas inside {} or []
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)

    # Convert Python triple-quoted strings into YAML block scalars
    def _triple_quote_to_block(m):
        indent = m.group(1)
        key_plus = m.group(2)
        body = m.group(3)
        colon_idx = key_plus.index(":")
        yaml_key = key_plus[: colon_idx + 1]
        value_prefix = key_plus[colon_idx + 1:].strip()
        content_lines = []
        if value_prefix:
            content_lines.append(value_prefix)
        content_lines.extend(body.strip().splitlines())
        indented = "\n".join(f"{indent}  {line}" for line in content_lines)
        return f"{indent}{yaml_key} |\n{indented}"

    raw = re.sub(
        r'^([ ]*)(\S+:[^\n]*)"""(.*?)"""',
        _triple_quote_to_block,
        raw,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Unbalanced double-quotes on a single line (odd count → append one)
    lines = raw.split("\n")
    fixed = []
    for line in lines:
        if line.count('"') % 2 != 0:
            line = line + '"'
        fixed.append(line)
    return "\n".join(fixed)


# ── Loader ────────────────────────────────────────────
def load_soul_yaml(path: str) -> dict:
    """
    Load a soul YAML from disk. If it fails to parse, attempt auto-repair
    and retry once. Returns the parsed dict or raises on total failure.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # First pass — normal parse
    try:
        soul = yaml.safe_load(raw)
        if isinstance(soul, dict):
            return soul
    except yaml.YAMLError:
        pass

    # Second pass — auto-repair then parse
    repaired = _attempt_repair(raw)
    try:
        soul = yaml.safe_load(repaired)
        if isinstance(soul, dict):
            return soul
    except yaml.YAMLError:
        pass

    raise ValueError(f"Could not parse soul YAML (even after auto-repair): {path}")


def load_soul_from_string(raw: str) -> dict:
    """Parse a soul YAML from a raw string (useful for APIs and testing)."""
    try:
        soul = yaml.safe_load(raw)
        if isinstance(soul, dict):
            return soul
    except yaml.YAMLError:
        pass

    repaired = _attempt_repair(raw)
    try:
        soul = yaml.safe_load(repaired)
        if isinstance(soul, dict):
            return soul
    except yaml.YAMLError:
        pass

    raise ValueError("Could not parse soul YAML string (even after auto-repair)")


# ── Soul → System Prompt ──────────────────────────────
def _flatten_value(val, indent=0) -> str:
    """Recursively turn any YAML value into readable text."""
    prefix = "  " * indent
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, list):
        items = []
        for item in val:
            flat = _flatten_value(item, indent)
            items.append(f"- {flat}")
        return "\n".join(f"{prefix}{i}" for i in items)
    if isinstance(val, dict):
        parts = []
        for k, v in val.items():
            key_label = str(k).replace("_", " ").title()
            flat = _flatten_value(v, indent + 1)
            if "\n" in flat:
                parts.append(f"{prefix}{key_label}:\n{flat}")
            else:
                parts.append(f"{prefix}{key_label}: {flat}")
        return "\n".join(parts)
    return str(val)


# Sections that map to readable prompt headings
_SECTION_HEADINGS = {
    "identity": "IDENTITY",
    "expression": "EXPRESSION & STYLE",
    "capabilities": "CAPABILITIES",
    "ethics": "ETHICS & VALUES",
    "relationship_dynamics": "RELATIONSHIPS",
    "relationship": "RELATIONSHIPS",
    "relationships": "RELATIONSHIPS",
    "scenario": "CURRENT SCENARIO",
    "location": "CURRENT LOCATION",
    "extras": "ADDITIONAL RULES",
    "persona": "PERSONA",
    "personality": "PERSONALITY",
    "backstory": "BACKSTORY",
    "lore": "LORE",
    "appearance": "APPEARANCE",
    "visuals": "APPEARANCE",
    "communication": "COMMUNICATION STYLE",
    "tools": "TOOLS & CAPABILITIES",
    "memory": "MEMORY & CONTEXT",
    "metadata": "METADATA",
}


def soul_to_system_prompt(soul: dict, base_prompt: str = "") -> str:
    """
    Walk the full soul dict and produce a rich system prompt.
    If base_prompt is given it's prepended as the foundation.
    Works with any soul schema version.
    """
    if not isinstance(soul, dict):
        return base_prompt

    name = extract_name(soul)
    parts = []

    if base_prompt:
        parts.append(base_prompt.strip())

    parts.append(f"=== SOUL FILE: {name} ===")

    for key, val in soul.items():
        heading = _SECTION_HEADINGS.get(key.lower(), key.replace("_", " ").upper())
        body = _flatten_value(val, indent=1)
        parts.append(f"\n[{heading}]\n{body}")

    parts.append(f"\n=== END SOUL ===")
    return "\n".join(parts)


def validate_soul(soul: dict) -> list:
    """
    Run basic validation on a soul dict. Returns a list of warnings (empty = valid).
    Doesn't enforce a rigid schema — just checks for common issues.
    """
    warnings = []
    if not isinstance(soul, dict):
        return ["Soul is not a dictionary"]

    name = extract_name(soul)
    if name == "Unknown":
        warnings.append("No identity/name field found — soul will load as 'Unknown'")

    # Check for empty top-level sections
    for key, val in soul.items():
        if val is None:
            warnings.append(f"Section '{key}' is empty (null)")

    return warnings
