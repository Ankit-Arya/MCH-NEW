@echo off
setlocal

set READONLY_USER=mch_readonly
set READONLY_PASSWORD=admin_password
set DB_NAME=mch_inspection
set DB_ADMIN_USER=mch_user
set POSTGRES_SERVICE=postgres

set SQL_FILE=%TEMP%\create_mch_readonly.sql

echo Creating / updating PostgreSQL readonly user: %READONLY_USER%

> "%SQL_FILE%" echo DO $$
>> "%SQL_FILE%" echo BEGIN
>> "%SQL_FILE%" echo   IF NOT EXISTS ^(SELECT 1 FROM pg_roles WHERE rolname = '%READONLY_USER%'^) THEN
>> "%SQL_FILE%" echo     CREATE ROLE %READONLY_USER% LOGIN PASSWORD '%READONLY_PASSWORD%';
>> "%SQL_FILE%" echo   ELSE
>> "%SQL_FILE%" echo     ALTER ROLE %READONLY_USER% WITH LOGIN PASSWORD '%READONLY_PASSWORD%';
>> "%SQL_FILE%" echo   END IF;
>> "%SQL_FILE%" echo END $$;
>> "%SQL_FILE%" echo.
>> "%SQL_FILE%" echo GRANT CONNECT ON DATABASE %DB_NAME% TO %READONLY_USER%;
>> "%SQL_FILE%" echo GRANT USAGE ON SCHEMA public TO %READONLY_USER%;
>> "%SQL_FILE%" echo GRANT SELECT ON ALL TABLES IN SCHEMA public TO %READONLY_USER%;
>> "%SQL_FILE%" echo ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO %READONLY_USER%;

docker compose exec -T %POSTGRES_SERVICE% psql -U %DB_ADMIN_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 < "%SQL_FILE%"

if errorlevel 1 (
    echo.
    echo Failed to create/update readonly user.
    exit /b 1
)

echo.
echo Done. Testing readonly login...
docker compose exec -T %POSTGRES_SERVICE% psql -U %READONLY_USER% -d %DB_NAME% -c "SELECT current_user, current_database();"

echo.
echo Restart API now:
echo docker compose restart api

endlocal