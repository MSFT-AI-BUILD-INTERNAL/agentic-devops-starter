"""Compatibility module for `src.runtime.skills`."""

import sys

from src.runtime import skills as _module

sys.modules[__name__] = _module
