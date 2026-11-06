<#
.SYNOPSIS
    Pushes this repository to your GitHub account.
.DESCRIPTION
    Uses GitHub CLI (gh) if authenticated, or prompts for your GitHub repository URL.
#>

param(
    [string]$RepoUrl,
    [string]$RepoName = "letta-antigravity-agent",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

$GhExe = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $GhExe)) {
    $GhExe = (Get-Command gh -ErrorAction SilentlyContinue)?.Source
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Pushing Letta AI Agent to GitHub                      " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Check if origin already exists
$CurrentRemote = git remote get-url origin 2>$null

if ($RepoUrl) {
    if ($CurrentRemote) {
        git remote set-url origin $RepoUrl
    } else {
        git remote add origin $RepoUrl
    }
    Write-Host "Set remote origin to: $RepoUrl" -ForegroundColor Green
    git branch -M main
    git push -u origin main
    exit $LASTEXITCODE
}

# If gh is available, check auth status
if ($GhExe -and (Test-Path $GhExe)) {
    & $GhExe auth status 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "GitHub CLI is authenticated." -ForegroundColor Green
        Write-Host "Creating repository '$RepoName' ($Visibility) on GitHub..." -ForegroundColor Yellow
        git branch -M main
        & $GhExe repo create $RepoName "--$Visibility" --source=. --remote=origin --push
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`nSuccessfully created and pushed to GitHub!" -ForegroundColor Green
            exit 0
        }
    } else {
        Write-Host "`nGitHub CLI is installed, but you are not logged in." -ForegroundColor Yellow
        Write-Host "To log in with your GitHub account, run:" -ForegroundColor Cyan
        Write-Host '  & "C:\Program Files\GitHub CLI\gh.exe" auth login' -ForegroundColor White
        Write-Host "`nAfter logging in, re-run this script to automatically create and push the repository." -ForegroundColor Yellow
    }
}

Write-Host "`nAlternative Manual Push Instructions:" -ForegroundColor Cyan
Write-Host "1. Create a new empty repository on https://github.com/new"
Write-Host "2. Run the following commands:"
Write-Host "   git remote add origin https://github.com/<YOUR-USERNAME>/$RepoName.git" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host "========================================================`n"
