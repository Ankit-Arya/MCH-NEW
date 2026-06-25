@echo off
setlocal

REM Run this CMD from the extracted patch folder placed in your project root.
python backend\scripts\apply_image_fullres_patch.py
if errorlevel 1 (
  echo.
  echo Patch failed. Check the message above.
  exit /b 1
)

echo.
echo Patch applied. Rebuild API using:
echo docker compose up -d --build api
endlocal
