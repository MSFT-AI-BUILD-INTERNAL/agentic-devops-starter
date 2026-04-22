"""Prompt manager for loading system prompts from YAML."""

import logging
from pathlib import Path

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _yaml = None  # type: ignore[assignment]
    _YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

_DEFAULT_PROMPTS_PATH = Path(__file__).parent / "system_prompts.yaml"
_DEFAULT_FALLBACK_KEY = "default.system"


class PromptManager:
    """Loads and resolves agent system prompts from a YAML file.

    Prompt keys follow the schema ``<agent_name>.<prompt_type>``.
    If the requested key is not found, falls back to ``default.system``.

    Usage::

        manager = PromptManager()
        prompt = manager.get("myagent.system")
    """

    def __init__(self, prompts_path: Path | None = None) -> None:
        self._prompts_path = prompts_path or _DEFAULT_PROMPTS_PATH
        self._prompts: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load prompts from the YAML file."""
        if not _YAML_AVAILABLE:
            logger.warning("PyYAML not installed; PromptManager will use built-in fallbacks only")
            self._prompts = {}
            return

        if not self._prompts_path.exists():
            logger.warning("Prompts file not found: %s", self._prompts_path)
            self._prompts = {}
            return

        with self._prompts_path.open(encoding="utf-8") as fh:
            data = _yaml.safe_load(fh)

        if not isinstance(data, dict) or "prompts" not in data:
            logger.warning("Invalid prompts YAML structure in %s", self._prompts_path)
            self._prompts = {}
            return

        self._prompts = {k: str(v).strip() for k, v in data["prompts"].items()}
        logger.info("Loaded %d prompts from %s", len(self._prompts), self._prompts_path)

    def get(self, key: str) -> str:
        """Return the prompt for *key*, falling back to ``default.system``.

        Args:
            key: Prompt key in the format ``<agent_name>.<prompt_type>``.

        Returns:
            The resolved prompt string.
        """
        if key in self._prompts:
            return self._prompts[key]

        logger.debug("Prompt key '%s' not found; using default.system fallback", key)
        return self._prompts.get(_DEFAULT_FALLBACK_KEY, "You are a helpful AI assistant.")
