param([switch]$NoLaunch)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousCargoHome = $env:CARGO_HOME
Push-Location -LiteralPath $projectRoot
try {
    $pythonTool = Join-Path $projectRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonTool)) { throw 'Project Python environment is missing. Run scripts/setup.ps1 first.' }
    $localToolsFile = Join-Path $projectRoot '.local-tools/toolchain.json'
    $localTools = if (Test-Path -LiteralPath $localToolsFile) { Get-Content -LiteralPath $localToolsFile -Raw | ConvertFrom-Json } else { $null }
    $nodeTool = (Get-Command node -ErrorAction SilentlyContinue).Source
    $cargoTool = (Get-Command cargo -ErrorAction SilentlyContinue).Source
    if (-not $nodeTool -and $localTools) { $nodeTool = $localTools.node }
    if (-not $cargoTool -and $localTools) { $cargoTool = $localTools.cargo }
    if (-not $nodeTool -or -not $cargoTool) { throw 'Node and Cargo must be available. Run setup from your configured development shell.' }
    & $pythonTool scripts/verify_runtime.py
    if ($LASTEXITCODE -ne 0) { throw 'Runtime verification failed' }
    & $nodeTool scripts/frontend.mjs build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    $env:CARGO_HOME = Join-Path $projectRoot '.local-tools/cargo-home'
    & $cargoTool build --offline --locked --features custom-protocol --manifest-path src-tauri/Cargo.toml
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed; no additional tools were installed' }
    if (-not $NoLaunch) { & (Join-Path $projectRoot 'src-tauri/target/debug/trading-terminal.exe') }
} finally {
    $env:CARGO_HOME = $previousCargoHome
    Pop-Location
}
