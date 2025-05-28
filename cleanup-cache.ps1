# PowerShell script to clean up development cache and build artifacts
# Run this from the project root directory

Write-Host "Cleaning up development cache files and build artifacts..." -ForegroundColor Green

# Remove Python cache directories
Get-ChildItem -Path . -Recurse -Name "__pycache__" -Directory | ForEach-Object {
    Write-Host "Removing: $_" -ForegroundColor Yellow
    Remove-Item -Path $_ -Recurse -Force
}

# Remove development tool caches
$cacheDirectories = @('.mypy_cache', '.pytest_cache', '.ruff_cache')
foreach ($dir in $cacheDirectories) {
    if (Test-Path $dir) {
        Write-Host "Removing: $dir" -ForegroundColor Yellow
        Remove-Item -Path $dir -Recurse -Force
    }
}

# Remove build artifacts (optional - uncomment if needed)
# if (Test-Path 'presidio_fastapi.egg-info') {
#     Write-Host "Removing: presidio_fastapi.egg-info" -ForegroundColor Yellow
#     Remove-Item -Path 'presidio_fastapi.egg-info' -Recurse -Force
# }

Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "Note: These files will be regenerated automatically when needed." -ForegroundColor Cyan
