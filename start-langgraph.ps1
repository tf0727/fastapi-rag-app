param(
    [int]$Port = 2026
)

$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv with Python 3.11 and run: .\.venv\Scripts\python.exe -m pip install -e ".[server]"'
}

Push-Location $PSScriptRoot
try {
    & $taskPython -m langgraph_cli dev --no-browser --port $Port
    if ($LASTEXITCODE -ne 0) {
        throw "LangGraph exited with code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
