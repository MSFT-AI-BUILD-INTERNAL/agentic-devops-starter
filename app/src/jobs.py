"""Compatibility module for `src.runtime.jobs`."""

import sys

from src.runtime import jobs as _module

sys.modules[__name__] = _module
