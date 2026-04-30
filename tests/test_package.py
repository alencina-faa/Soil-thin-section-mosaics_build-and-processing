import importlib


def test_package_importable():
    pkg = importlib.import_module("stsm")
    assert pkg is not None


def test_main_entrypoint_exposed():
    pkg = importlib.import_module("stsm")
    assert hasattr(pkg, "main")
