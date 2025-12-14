@echo off
echo ====================================
echo  Adding Church Subdomains to Hosts
echo ====================================
echo.
echo This will add these entries:
echo   127.0.0.1 testchurch.localhost
echo   127.0.0.1 olamchurch.localhost
echo   127.0.0.1 deeperlifeministries.localhost
echo.
echo IMPORTANT: This requires Administrator privileges!
echo.
pause

:: Add entries to hosts file
echo 127.0.0.1 testchurch.localhost >> C:\Windows\System32\drivers\etc\hosts
echo 127.0.0.1 olamchurch.localhost >> C:\Windows\System32\drivers\etc\hosts
echo 127.0.0.1 deeperlifeministries.localhost >> C:\Windows\System32\drivers\etc\hosts

echo.
echo ====================================
echo  SUCCESS! Hosts file updated
echo ====================================
echo.
echo Now you can access:
echo   http://testchurch.localhost:8000/api/docs/
echo   http://olamchurch.localhost:8000/api/docs/
echo.
pause




