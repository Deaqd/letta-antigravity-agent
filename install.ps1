<#
.SYNOPSIS
    One-Command Automated Installer for Letta AI Agent in Google Antigravity.
.DESCRIPTION
    Installs virtual environment, dependencies, global MCP server configuration,
    and Antigravity UI agent integration.
#>

param(
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Letta AI Agent Installer for Google Antigravity      " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# 1. Verify Python
Write-Host "`n[1/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVer = python --version 2>&1
    Write-Host "Found: $pythonVer" -ForegroundColor Green
} catch {
    Write-Error "Python 3.10+ is required but not found on PATH. Please install Python and try again."
}

# 2. Virtual Environment Setup
Write-Host "`n[2/6] Setting up virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path "$ProjectRoot\.venv")) {
    python -m venv .venv
    Write-Host "Created virtual environment." -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

$VenvPython = "$ProjectRoot\.venv\Scripts\python.exe"
$VenvPip = "$ProjectRoot\.venv\Scripts\pip.exe"

# 3. Install Package and Dependencies
Write-Host "`n[3/6] Installing dependencies..." -ForegroundColor Yellow
& $VenvPip install --upgrade pip --quiet
& $VenvPip install -e . --quiet
Write-Host "Installed letta-antigravity-integration successfully." -ForegroundColor Green

# 4. Storage Directory Setup
Write-Host "`n[4/6] Initializing storage directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$ProjectRoot\data" | Out-Null
if (-not (Test-Path "$ProjectRoot\.env")) {
    Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
    Write-Host "Created .env from template." -ForegroundColor Green
}

# 5. Global Antigravity Integration
Write-Host "`n[5/6] Registering global Antigravity MCP Server and UI Agent..." -ForegroundColor Yellow
$GlobalGeminiConfig = "$env:USERPROFILE\.gemini\config"
$GlobalMcpConfig = "$GlobalGeminiConfig\mcp_config.json"
$GlobalPluginsDir = "$GlobalGeminiConfig\plugins\letta-agent"

New-Item -ItemType Directory -Force -Path "$GlobalPluginsDir\agents", "$GlobalPluginsDir\rules", "$GlobalPluginsDir\skills\letta" | Out-Null
Copy-Item -Recurse -Force "$ProjectRoot\plugins\letta-agent\*" "$GlobalPluginsDir\"

# Update mcp_config.json
$McpConfigData = @{
    mcpServers = @{
        "letta-agent" = @{
            command = $VenvPython
            args = @("-m", "letta_integration.server.mcp_server")
            env = @{
                PYTHONPATH = "$ProjectRoot\src"
                LETTA_MODE = "auto"
                LETTA_STORAGE_PATH = "$ProjectRoot\data\letta_storage.db"
            }
        }
    }
}
$McpConfigJson = $McpConfigData | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($GlobalMcpConfig, $McpConfigJson, [System.Text.Encoding]::UTF8)

# Update config.json to ensure plugin is enabled
$ConfigFile = "$GlobalGeminiConfig\config.json"
if (Test-Path $ConfigFile) {
    try {
        $Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        if (-not $Config.plugins) {
            $Config | Add-Member -MemberType NoteProperty -Name "plugins" -Value ([PSCustomObject]@{})
        }
        if (-not $Config.plugins."letta-agent") {
            $Config.plugins | Add-Member -MemberType NoteProperty -Name "letta-agent" -Value ([PSCustomObject]@{
                installedFrom = [PSCustomObject]@{
                    id = "letta-agent"
                    version = "1.0.0"
                }
            })
            $UpdatedJson = $Config | ConvertTo-Json -Depth 10
            [System.IO.File]::WriteAllText($ConfigFile, $UpdatedJson, [System.Text.Encoding]::UTF8)
        }
    } catch {
        Write-Warning "Could not automatically patch config.json: $_"
    }
}
Write-Host "Registered in ~/.gemini/config/mcp_config.json and UI agents menu." -ForegroundColor Green

# 6. Run Test Verification
if (-not $SkipTests) {
    Write-Host "`n[6/6] Running validation test suite..." -ForegroundColor Yellow
    $env:PYTHONPATH = "$ProjectRoot\src"
    & "$ProjectRoot\.venv\Scripts\pytest.exe" -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "All automated tests PASSED!" -ForegroundColor Green
    } else {
        Write-Warning "Some tests did not pass. Check test logs."
    }
} else {
    Write-Host "`n[6/6] Skipped tests as requested." -ForegroundColor DarkGray
}

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "  INSTALLATION COMPLETE!                                " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "How to use:"
Write-Host "1. In Antigravity, click the Agent selector dropdown (bottom left of chat)."
Write-Host "2. Hover over 'Main Agent >' and select 'letta-agent'."
Write-Host "3. Start chatting! All persistent memories will be stored automatically."
Write-Host "========================================================`n"
