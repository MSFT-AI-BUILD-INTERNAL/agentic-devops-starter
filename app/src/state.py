"""Compatibility module for `src.runtime.state`."""

import sys

from src.runtime import state as _module

sys.modules[__name__] = _module
