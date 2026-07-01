"""Compatibility module for `src.core.config`."""

import sys

from src.core import config as _module

sys.modules[__name__] = _module
