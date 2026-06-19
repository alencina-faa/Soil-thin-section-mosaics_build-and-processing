try:
    from .app import main
except ImportError:
    from app import main  # type: ignore[reportMissingImports]

if __name__ == "__main__":
    main()
