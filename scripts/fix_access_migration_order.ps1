$ErrorActionPreference = "Stop"

$old = "backend/alembic/versions/0002_access_hierarchy.py"
$new = "backend/alembic/versions/0003_access_hierarchy.py"

if (Test-Path $old) {
  Write-Host "Removing old branching migration: $old"
  Remove-Item $old -Force
}

if (!(Test-Path $new)) {
  Write-Host "ERROR: $new not found. Copy the patch files into project root first." -ForegroundColor Red
  exit 1
}

Write-Host "Migration chain should now be:" -ForegroundColor Green
Write-Host "0001_initial_schema -> 0002_add_inspection_entries -> 0003_access_hierarchy"
Write-Host "Now run: docker compose exec api alembic upgrade head"
