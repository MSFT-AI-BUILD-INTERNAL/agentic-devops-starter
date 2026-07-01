"""Compatibility module for `src.core.logging_utils`."""

import sys

from src.core import logging_utils as _module

sys.modules[__name__] = _module
