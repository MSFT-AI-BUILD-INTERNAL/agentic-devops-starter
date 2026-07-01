"""Compatibility module for `src.storage.blob_storage`."""

import sys

from src.storage import blob_storage as _module

sys.modules[__name__] = _module
