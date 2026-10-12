$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BuildDrive = $null

try {
    $DriveLetter = @("Z", "Y", "X", "W", "V", "U") |
        Where-Object { -not (Get-PSDrive -Name $_ -ErrorAction SilentlyContinue) } |
        Select-Object -First 1
    if (-not $DriveLetter) {
        throw "没有可用于构建的空闲盘符（Z: 到 U:）。"
    }
    $BuildDrive = "${DriveLetter}:"
    & subst $BuildDrive $Root
    if ($LASTEXITCODE -ne 0) {
        throw "无法为项目创建 ASCII 构建路径。"
    }
    $BuildRoot = "$BuildDrive\"
    Push-Location $BuildRoot

    try {
    $Python = Join-Path $BuildRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $Python)) {
        $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $PythonCommand) {
            throw "未找到 Python。请先安装 Python 3.10 或更新版本。"
        }
        $Python = $PythonCommand.Source
    }

    & $Python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "安装构建依赖失败。"
    }

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name LinuxManual `
        --paths (Join-Path $BuildRoot "src") `
        --add-data "$(Join-Path $BuildRoot 'assets\icon.svg');assets" `
        --add-data "$(Join-Path $BuildRoot 'data\seed.json');data" `
        --specpath (Join-Path $BuildRoot "build\pyinstaller-windows") `
        --distpath (Join-Path $BuildRoot "dist") `
        --workpath (Join-Path $BuildRoot "build\pyinstaller-windows") `
        (Join-Path $BuildRoot "app.py")
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 构建失败。"
    }

    Write-Host "构建完成：$(Join-Path $Root 'dist\LinuxManual.exe')"
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($BuildDrive) {
        & subst $BuildDrive /D
    }
}