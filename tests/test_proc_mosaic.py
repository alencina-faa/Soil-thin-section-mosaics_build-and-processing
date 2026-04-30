import cv2
import numpy as np
import pytest

from stsm.proc_mosaic import detect_edge_contours_optimized, enhanced_process_mosaic_optimized


def test_detect_edge_contours_flags_border_contact():
    image = np.zeros((30, 30), dtype=np.uint8)

    # One contour touches the left border and one is fully internal.
    touching = np.array([[[0, 5]], [[0, 10]], [[6, 10]], [[6, 5]]], dtype=np.int32)
    internal = np.array([[[15, 15]], [[15, 20]], [[20, 20]], [[20, 15]]], dtype=np.int32)

    result = detect_edge_contours_optimized(image, [touching, internal], border_size=1)

    assert result == [True, False]


def test_enhanced_process_mosaic_returns_empty_for_blank_image():
    image = np.zeros((32, 32), dtype=np.uint8)

    processed = enhanced_process_mosaic_optimized(image)

    assert processed == []


def test_enhanced_process_mosaic_tracks_parent_and_child_contours():
    image = np.zeros((80, 80), dtype=np.uint8)

    # Build a donut shape: one parent contour with one child contour (hole).
    cv2.circle(image, (40, 40), 24, 255, -1)
    cv2.circle(image, (40, 40), 10, 0, -1)

    processed = enhanced_process_mosaic_optimized(image)

    assert len(processed) == 1

    idx, is_edge, parent, children, final_area, final_perimeter = processed[0]
    assert idx == 0
    assert is_edge is False
    assert len(children) == 1

    expected_area = cv2.contourArea(parent) - cv2.contourArea(children[0])
    expected_perimeter = cv2.arcLength(parent, True) + cv2.arcLength(children[0], True)

    assert final_area == pytest.approx(expected_area)
    assert final_perimeter == pytest.approx(expected_perimeter)
