param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousCargoHome = $env:CARGO_HOME
Push-Location -LiteralPath $projectRoot
try {
    $nodeTool = (Get-Command node -ErrorAction Stop).Source
    $cargoTool = (Get-Command cargo -ErrorAction Stop).Source
    $pnpmTool = (Get-Command pnpm -ErrorAction Stop).Source
    if ((& $nodeTool --version) -ne 'v24.19.0') { throw 'Validated Node version is 24.19.0. System tools were not changed.' }
    if ((& $pnpmTool --version) -ne '11.19.0') { throw 'Validated pnpm version is 11.19.0. System tools were not changed.' }
    if (-not (Test-Path -LiteralPath '.venv')) {
        & $Python -c "import sys,platform; assert sys.version_info[:2]==(3,12) and platform.machine().lower() in ('amd64','x86_64')"
        if ($LASTEXITCODE -ne 0) { throw 'Provide an installed CPython 3.12 x64 interpreter with -Python' }
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
        & .venv/Scripts/python.exe -m pip install --require-hashes --only-binary=:all: --index-url https://pypi.org/simple --cache-dir .local-tools/pip-cache --requirement requirements/runtime-windows-py312.lock --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) { throw 'Pinned package installation failed' }
    }
    & .venv/Scripts/python.exe scripts/verify_runtime.py
    if ($LASTEXITCODE -ne 0) { throw 'Existing Python environment differs; setup has preserved it' }
    & $pnpmTool install --frozen-lockfile --ignore-scripts --store-dir .local-tools/pnpm-store
    if ($LASTEXITCODE -ne 0) { throw 'Pinned frontend installation failed' }
    $env:CARGO_HOME = Join-Path $projectRoot '.local-tools/cargo-home'
    & $cargoTool fetch --locked --target x86_64-pc-windows-msvc --manifest-path src-tauri/Cargo.toml
    if ($LASTEXITCODE -ne 0) { throw 'Pinned Rust dependency fetch failed' }
    New-Item -ItemType Directory -Path '.local-tools' -Force | Out-Null
    @{ node=$nodeTool; cargo=$cargoTool } | ConvertTo-Json | Set-Content -LiteralPath '.local-tools/toolchain.json' -Encoding utf8
    Write-Output 'Project dependencies prepared. Run .\scripts\launch.ps1 to build and open the application.'
} finally {
    $env:CARGO_HOME = $previousCargoHome
    Pop-Location
}
