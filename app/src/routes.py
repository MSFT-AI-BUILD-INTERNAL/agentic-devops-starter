"""Compatibility module for `src.api.routes`."""

import sys

from src.api import routes as _module

sys.modules[__name__] = _module
