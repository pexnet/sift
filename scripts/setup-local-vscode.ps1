param(
    [string]$ExtensionsFile = ".vscode/extensions.local.json"
)

$codeCmd = Get-Command code -ErrorAction SilentlyContinue
if (-not $codeCmd) {
    Write-Host "VS Code CLI ('code') is not available. Install it and rerun this script."
    exit 1
}

if (-not (Test-Path $ExtensionsFile)) {
    Write-Host "No local extensions file found at $ExtensionsFile"
    Write-Host "Create it from .vscode/extensions.local.example.json first."
    exit 0
}

$config = Get-Content -Raw -Path $ExtensionsFile | ConvertFrom-Json
$extensions = @()

if ($config -is [System.Array]) {
    $extensions = $config
}
elseif ($null -ne $config.extensions) {
    $extensions = $config.extensions
}

if ($extensions.Count -eq 0) {
    Write-Host "No extensions defined in $ExtensionsFile"
    exit 0
}

foreach ($extension in $extensions) {
    Write-Host "Installing $extension"
    code --install-extension $extension --force
}
