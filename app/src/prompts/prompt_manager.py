"""Prompt manager for centralized agent prompt loading.

Loads agent prompts from system_prompts.yaml so that prompt definitions
are never hardcoded in application code. This enables prompt changes without
requiring code modifications.
"""

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent
_DEFAULT_YAML_FILE = _PROMPTS_DIR / "system_prompts.yaml"


def _parse_yaml_prompts(content: str) -> dict[str, str]:
    """Parse the prompts YAML file into a flat key→value dict.

    Uses a minimal hand-rolled parser to avoid requiring a PyYAML dependency.
    The YAML schema is intentionally simple: a top-level ``prompts:`` mapping
    where each value is a literal block scalar (``|``).
    """
    prompts: dict[str, str] = {}

    # Match entries of the form:
    #   <key>: |
    #     <indented content>
    # The key is indented with any consistent whitespace under "prompts:".
    pattern = re.compile(
        r"^( {2,})(\S+):\s*\|\n((?:\1 [^\n]*\n)*)",
        re.MULTILINE,
    )
    for match in pattern.finditer(content):
        key_indent = match.group(1)  # e.g. "  "
        key = match.group(2)
        # Content lines are indented one extra level beyond key_indent
        content_indent = len(key_indent) + 1
        lines = [
            line[content_indent:] if len(line) > content_indent else line.lstrip()
            for line in match.group(3).splitlines()
        ]
        prompts[key] = "\n".join(lines).strip()

    return prompts


class PromptManager:
    """Loads and provides agent system prompts from a centralized YAML file.

    Usage::

        manager = PromptManager()
        prompt = manager.get("agui_assistant.system")
    """

    _DEFAULT_KEY = "default.system"

    def __init__(self, yaml_path: Path | None = None) -> None:
        path = yaml_path or _DEFAULT_YAML_FILE
        self._prompts = _parse_yaml_prompts(path.read_text(encoding="utf-8"))

    def get(self, key: str) -> str:
        """Return the prompt for *key*, falling back to the default prompt.

        Args:
            key: Prompt key in the form ``<agent>.<type>`` (e.g. ``agui_assistant.system``).

        Returns:
            The prompt string.

        Raises:
            KeyError: If *key* AND the default key are both missing.
        """
        if key in self._prompts:
            return self._prompts[key]
        if self._DEFAULT_KEY in self._prompts:
            return self._prompts[self._DEFAULT_KEY]
        raise KeyError(f"Prompt key '{key}' not found and no default prompt is defined")

    def list_keys(self) -> list[str]:
        """Return all available prompt keys."""
        return list(self._prompts.keys())
