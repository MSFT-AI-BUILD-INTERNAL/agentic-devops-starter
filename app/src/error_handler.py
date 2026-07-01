"""Compatibility module for `src.api.error_handler`."""

import sys

from src.api import error_handler as _module

sys.modules[__name__] = _module
