param(
    [switch]$Fix
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
$PyCmd = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

& $PyCmd -m pip install -e .[dev]

if ($Fix) {
    & $PyCmd -m ruff check src tests --fix
    & $PyCmd -m black src tests
}

& $PyCmd -m ruff check src tests
& $PyCmd -m black --check src tests
& $PyCmd -m pytest -q

Write-Host "QA checks passed." -ForegroundColor Green
