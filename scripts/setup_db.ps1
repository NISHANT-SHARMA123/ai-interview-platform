# =============================================================================
# PowerShell Script: Provision PostgreSQL Database & Least-Privilege User
# =============================================================================
param(
    [string]$SuperUser = "postgres",
    [string]$HostName = "localhost",
    [string]$Port = "5432"
)

Write-Host ">>> Executing PostgreSQL provisioning script via psql..." -ForegroundColor Cyan

$scriptPath = Join-Path $PSScriptRoot "setup_postgres.sql"
& psql -h $HostName -p $Port -U $SuperUser -f $scriptPath

if ($LASTEXITCODE -eq 0) {
    Write-Host ">>> Database 'mock_interview_db' and user 'interview_app_user' successfully provisioned!" -ForegroundColor Green
} else {
    Write-Host ">>> Provisioning failed or requires manual password input. Please check credentials." -ForegroundColor Yellow
}
