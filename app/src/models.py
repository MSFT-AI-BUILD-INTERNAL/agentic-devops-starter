"""Compatibility module for `src.api.models`."""

import sys

from src.api import models as _module

sys.modules[__name__] = _module
