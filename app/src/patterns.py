"""Compatibility module for `src.teams.patterns`."""

import sys

from src.teams import patterns as _module

sys.modules[__name__] = _module
