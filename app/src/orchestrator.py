"""Compatibility module for `src.teams.orchestrator`."""

import sys

from src.teams import orchestrator as _module

sys.modules[__name__] = _module
