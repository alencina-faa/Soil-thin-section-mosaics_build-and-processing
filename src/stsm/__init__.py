"""stsm package."""

from .proc_mosaic import detect_edge_contours_optimized, enhanced_process_mosaic_optimized


def main():
    """Package-level entrypoint forwarded lazily to avoid eager GUI imports."""
    from .app import main as app_main

    return app_main()

__all__ = [
    "detect_edge_contours_optimized",
    "enhanced_process_mosaic_optimized",
    "main",
]
