# ═══════════════════════════════════════════════════════
#  AETHER + LEON — Register Windows Startup via Task Scheduler
#  Run this once as Administrator to register the auto-start task.
#  Then it will launch automatically whenever you log in.
# ═══════════════════════════════════════════════════════

$workspace = "c:\Users\saali\Documents\antigravity\charming-lovelace"
$startScript = "$workspace\scripts\start_aether.bat"
$taskName = "AETHER_Autonomous_Operator"
$logDir = "$workspace\data\logs"

# Create logs directory if missing
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Remove old task if exists
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Define the action: run our bat file
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$startScript`"" `
    -WorkingDirectory $workspace

# Trigger: at user logon (works when laptop opens/unlocks)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings: run with lowest privileges, hidden, restart on failure
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew `
    -Hidden

# Register the task
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts AETHER + LEON autonomous operator on login" `
    -RunLevel Limited `
    -Force

Write-Host ""
Write-Host "✅ AETHER startup task registered: '$taskName'" -ForegroundColor Green
Write-Host "   It will auto-start every time you log in to Windows." -ForegroundColor Cyan
Write-Host "   Server: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "   To remove: Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Gray
