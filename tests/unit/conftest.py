"""Shared helpers for custom-module tests."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_module(name):
    path = ROOT / "library" / ("%s.py" % name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def yaml_module():
    return load_module("users_from_yaml")


@pytest.fixture(scope="session")
def hcv_module():
    return load_module("users_from_hcv")
