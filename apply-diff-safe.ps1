<#
.SYNOPSIS
Safely apply and auto-commit a Git patch (diff) file or inline text.

.DESCRIPTION
- Verifies Git repository
- Creates backup branch
- Validates patch (dry-run + 3-way fallback)
- Applies patch
- Auto-stages and commits changes
#>

param(
    [string]$PatchFile
)

$ErrorActionPreference = "Stop"

# Step 1: Verify inside Git repo
if (-not (git rev-parse --is-inside-work-tree 2>$null)) {
    Write-Host "ERROR: Not inside a Git repository." -ForegroundColor Red
    exit 1
}

# Step 2: Move to repo root
$RepoRoot = git rev-parse --show-toplevel
Set-Location $RepoRoot

# Step 3: Create backup branch
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupBranch = "pre-patch-$Timestamp"
git branch $BackupBranch | Out-Null
Write-Host ("Backup branch created: {0}" -f $BackupBranch) -ForegroundColor Cyan

# Step 4: Read diff (from file or piped input)
$TempPatch = New-TemporaryFile
if ($PatchFile -and (Test-Path $PatchFile)) {
    Get-Content -Raw $PatchFile | Out-File -Encoding utf8 $TempPatch
} else {
    $input | Out-File -Encoding utf8 $TempPatch
}

# Step 5: Dry-run test
Write-Host "Checking patch applicability..." -ForegroundColor Yellow
git apply --check $TempPatch 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dry-run failed. Trying 3-way merge check..." -ForegroundColor Yellow
    git apply --3way --check $TempPatch 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Patch cannot be applied cleanly, even with 3-way merge." -ForegroundColor Red
        Write-Host ("Backup branch preserved: {0}" -f $BackupBranch)
        Remove-Item $TempPatch -Force
        exit 1
    }
}

# Step 6: Apply patch
Write-Host "Applying patch..." -ForegroundColor Green
git apply --3way $TempPatch

# Step 7: Stage and commit
Write-Host ""
Write-Host "Staging and committing changes..." -ForegroundColor Cyan
git add -A
$CommitMsg = "Applied diff safely - $Timestamp"
git commit -m "$CommitMsg"

# Step 8: Summary
Write-Host ""
Write-Host "Patch applied and committed successfully." -ForegroundColor Green
Write-Host ("Commit message: {0}" -f $CommitMsg)
Write-Host ""
Write-Host "Git status:" -ForegroundColor Cyan
git status -s
Write-Host ""
Write-Host ("To undo, run: git switch {0}" -f $BackupBranch) -ForegroundColor Yellow

# Cleanup
Remove-Item $TempPatch -Force
