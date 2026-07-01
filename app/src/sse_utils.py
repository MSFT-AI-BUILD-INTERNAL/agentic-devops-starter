"""Compatibility module for `src.api.sse_utils`."""

import sys

from src.api import sse_utils as _module

sys.modules[__name__] = _module
