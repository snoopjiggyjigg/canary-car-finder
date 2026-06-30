param(
    [switch]$NoOpen,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Stop-Build {
    param([string]$Message)
    Write-Host ""
    Write-Host "Build failed:" -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    if (-not $NoPause) {
        Write-Host ""
        Read-Host "Press Enter to close"
    }
    exit 1
}

function Remove-BuildPath {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

try {
    $appName = (& python -c "from app_config import APP_NAME; print(APP_NAME)").Trim()
    $version = (& python -c "from app_config import APP_VERSION; print(APP_VERSION)").Trim()
    if (-not $appName) { Stop-Build "Could not read the application name from app_config.py." }
    if (-not $version) { Stop-Build "Could not read the application version from app_config.py." }

    $versionTag = if ($version.StartsWith("v")) { $version } else { "v$version" }
    $releaseName = "Canary-Islands-Car-Hire-Optimiser-$versionTag"
    $releaseRoot = Join-Path $PSScriptRoot "release"
    $releaseFolder = Join-Path $releaseRoot $releaseName
    $zipPath = Join-Path $releaseRoot "$releaseName.zip"
    $distRoot = Join-Path $PSScriptRoot "dist"
    $distFolder = Join-Path $distRoot $appName
    $exePath = Join-Path $releaseFolder "$appName.exe"

    Write-Host "Building $appName $versionTag" -ForegroundColor Cyan
    Write-Host "Cleaning old build folders..."
    Remove-BuildPath (Join-Path $PSScriptRoot "build")
    Remove-BuildPath $distRoot
    Remove-BuildPath $releaseFolder
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

    Write-Host "Running PyInstaller..."
    & python -m PyInstaller --clean --noconfirm CanaryCarFinder.spec
    if ($LASTEXITCODE -ne 0) {
        Stop-Build "PyInstaller returned exit code $LASTEXITCODE."
    }
    if (-not (Test-Path -LiteralPath $distFolder)) {
        Stop-Build "PyInstaller did not create the expected folder: $distFolder"
    }

    Write-Host "Creating release folder..."
    Copy-Item -LiteralPath $distFolder -Destination $releaseFolder -Recurse -Force

    Write-Host "Copying config and assets..."
    $releaseConfig = Join-Path $releaseFolder "config"
    New-Item -ItemType Directory -Path $releaseConfig -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "config\app_config.json") -Destination $releaseConfig -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "config\default_settings.json") -Destination $releaseConfig -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "assets") -Destination (Join-Path $releaseFolder "assets") -Recurse -Force

    $readmeFirst = @"
Thank you for trying Canary Islands Car Hire Optimiser.

Getting Started

1. Extract the ZIP.
2. Double-click "Canary Islands Car Hire Optimiser.exe"

That's it.

This application compares prices from four trusted local Canary Islands car hire companies.

Some searches can take several minutes because prices are collected live from the providers' websites.

Feedback is always welcome.
"@
    Set-Content -LiteralPath (Join-Path $releaseFolder "README FIRST.txt") -Value $readmeFirst -Encoding UTF8

    if (-not (Test-Path -LiteralPath $exePath)) {
        Stop-Build "The branded executable was not found: $exePath"
    }

    Write-Host "Validating executable launch..."
    $process = Start-Process -FilePath $exePath -WorkingDirectory $releaseFolder -PassThru
    Start-Sleep -Seconds 6
    if ($process.HasExited) {
        Stop-Build "The executable started and then exited immediately. Exit code: $($process.ExitCode)"
    }
    $closed = $process.CloseMainWindow()
    Start-Sleep -Seconds 2
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }

    Write-Host "Creating ZIP package..."
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($releaseFolder, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)

    if (-not (Test-Path -LiteralPath $zipPath)) {
        Stop-Build "ZIP package was not created: $zipPath"
    }

    Write-Host ""
    Write-Host "Build complete." -ForegroundColor Green
    Write-Host "Version: $versionTag"
    Write-Host "EXE location: $exePath"
    Write-Host "ZIP location: $zipPath"

    if (-not $NoOpen) {
        Invoke-Item -LiteralPath $releaseFolder
    }

    if (-not $NoPause) {
        Write-Host ""
        Read-Host "Press Enter to close"
    }
}
catch {
    Stop-Build $_.Exception.Message
}
