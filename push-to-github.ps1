# Script to push to GitHub
# First, create a Personal Access Token at: https://github.com/settings/tokens/new
# Select the 'repo' scope

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$repoPath = "C:\Users\mdsin\candidate-triage-system"
cd $repoPath

# Configure git to use the token
$remoteUrl = "https://${Token}@github.com/mattds34/candidate-triage-system.git"
git remote set-url origin $remoteUrl

# Push to GitHub
git push -u origin main

Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
Write-Host "View your repo at: https://github.com/mattds34/candidate-triage-system" -ForegroundColor Cyan
