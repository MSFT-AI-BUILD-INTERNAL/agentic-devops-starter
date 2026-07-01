"""Compatibility module for `src.core.observability`."""

import sys

from src.core import observability as _module

sys.modules[__name__] = _module
