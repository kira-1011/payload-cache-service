"""Guards the build config: both modules must be installed from src/ by uv_build."""

import importlib

import pytest


@pytest.mark.parametrize("module_name", ["cache_service", "cache_cli"])
def test_package_is_importable(module_name: str) -> None:
    assert importlib.import_module(module_name).__doc__
