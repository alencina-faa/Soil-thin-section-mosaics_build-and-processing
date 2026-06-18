import types
from pathlib import Path

import h5py
import numpy as np
import pytest

from stsm import proc_mosaic
from stsm.load_save import save_enhanced_contours_hdf5


class _FakePixelInput:
    def __init__(self, value):
        self._value = str(value)

    def get(self):
        return self._value


class _FakeBoolVar:
    def __init__(self, value=True):
        self._value = value

    def get(self):
        return self._value


class _FakeButton:
    def config(self, **kwargs):
        return None


class _DummyApp:
    pass


def _make_dummy_app(calibration_px_per_um=2.0):
    app = _DummyApp()
    app.pixel_cal_input = _FakePixelInput(calibration_px_per_um)
    app.proc_layer_visibility = [_FakeBoolVar(True) for _ in range(3)]
    app.save_mosaic_stats_data_button = _FakeButton()
    return app


def test_process_mosaic_stores_metrics_in_microns(monkeypatch):
    app = _make_dummy_app(calibration_px_per_um=2.0)

    # One contour group with known area/perimeter in px units.
    parent = np.array([[[1, 1]], [[1, 5]], [[5, 5]], [[5, 1]]], dtype=np.int32)
    child = np.array([[[2, 2]], [[2, 3]], [[3, 3]], [[3, 2]]], dtype=np.int32)
    processed_px = [[0, False, parent, [child], 200.0, 80.0]]

    monkeypatch.setattr(
        proc_mosaic,
        "enhanced_process_mosaic_optimized",
        lambda image: processed_px,
    )

    # Skip heavy post-processing for this unit-conversion-focused test.
    monkeypatch.setattr(proc_mosaic, "proc_cont_all", lambda self: None)
    monkeypatch.setattr(proc_mosaic, "proc_cont_great_50", lambda self: None)

    # Neutralize drawing/conversion calls.
    monkeypatch.setattr(proc_mosaic.cv2, "cvtColor", lambda img, code: img)
    monkeypatch.setattr(proc_mosaic.cv2, "drawContours", lambda *args, **kwargs: None)

    image = np.zeros((20, 20), dtype=np.uint8)
    proc_mosaic.process_mosaic(app, image)

    stored = app.processed_contours[0]
    assert stored[4] == pytest.approx(50.0)  # 200 / 2^2 -> um^2
    assert stored[5] == pytest.approx(40.0)  # 80 / 2 -> um

    expected_area_50_um2 = np.pi * (50.0 / 2.0) ** 2
    assert app.area_50 == pytest.approx(expected_area_50_um2)


def test_save_hdf5_does_not_double_convert_micron_metrics(tmp_path, monkeypatch):
    app = _make_dummy_app(calibration_px_per_um=2.0)

    parent = np.array([[[1, 1]], [[1, 5]], [[5, 5]], [[5, 1]]], dtype=np.int32)
    child = np.array([[[2, 2]], [[2, 3]], [[3, 3]], [[3, 2]]], dtype=np.int32)

    # Already in microns: area=50 um^2, perimeter=40 um.
    app.processed_contours = [[0, False, parent, [child], 50.0, 40.0]]
    app.calibration = 2.0

    # Avoid GUI side effects in tests.
    from stsm import load_save as load_save_module

    monkeypatch_info = types.SimpleNamespace(calls=[])

    def _record_showinfo(*args, **kwargs):
        monkeypatch_info.calls.append((args, kwargs))

    monkeypatch.setattr(load_save_module.messagebox, "showinfo", _record_showinfo)
    monkeypatch.setattr(load_save_module.messagebox, "showwarning", lambda *args, **kwargs: None)
    monkeypatch.setattr(load_save_module.messagebox, "showerror", lambda *args, **kwargs: None)

    output_dir = Path(tmp_path)
    mosaic_name = "mosaic_test"

    save_enhanced_contours_hdf5(app, str(output_dir), mosaic_name)

    h5_path = output_dir / mosaic_name / f"{mosaic_name}.h5"
    assert h5_path.exists()

    with h5py.File(h5_path, "r") as f:
        cg = f["contours"]["0"]
        assert float(cg.attrs["area"]) == pytest.approx(50.0)
        assert float(cg.attrs["perimeter"]) == pytest.approx(40.0)
        assert str(cg.attrs["area_unit"]) == "μm^2"
        assert str(cg.attrs["perimeter_unit"]) == "μm"
