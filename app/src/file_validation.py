"""Compatibility module for `src.storage.file_validation`."""

import sys

from src.storage import file_validation as _module

sys.modules[__name__] = _module
