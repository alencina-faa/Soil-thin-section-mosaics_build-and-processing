param(
    [switch]$Fix
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
$PyCmd = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

function Invoke-CheckedPython {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

Invoke-CheckedPython "Dependency installation" { & $PyCmd -m pip install -e ".[dev]" }

if ($Fix) {
    Invoke-CheckedPython "Ruff autofix" { & $PyCmd -m ruff check src tests --fix }
    Invoke-CheckedPython "Black formatting" { & $PyCmd -m black src tests }
}

Invoke-CheckedPython "Ruff check" { & $PyCmd -m ruff check src tests }
Invoke-CheckedPython "Black check" { & $PyCmd -m black --check src tests }
Invoke-CheckedPython "Pytest" { & $PyCmd -m pytest -q }

Write-Host "QA checks passed." -ForegroundColor Green
