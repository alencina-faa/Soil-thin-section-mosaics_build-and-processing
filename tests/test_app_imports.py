import pytest


def test_stsm_app_imports_in_package_mode():
    pytest.importorskip("tkinter")

    import stsm.app

    assert stsm.app is not None
    assert hasattr(stsm.app, "binary_tab")
    assert hasattr(stsm.app, "processing_tab")
    assert hasattr(stsm.app, "visualize_tab")
    assert callable(stsm.app.binary_tab)
    assert callable(stsm.app.processing_tab)
    assert callable(stsm.app.visualize_tab)
