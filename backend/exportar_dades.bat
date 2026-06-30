@echo off
echo ==========================================
echo  Exportar dades de Fitxes Tecniques
echo ==========================================
echo.

cd /d P:\fitxestecniques\backend

echo [1/3] Exportant base de dades...
pg_dump -U postgres -F c fitxes_tecniques > fitxes_backup.dump
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: No s'ha pogut exportar la BD. Verifica que PostgreSQL esta actiu.
    pause
    exit /b 1
)
echo OK: fitxes_backup.dump creat

echo.
echo [2/3] Comprimint carpeta uploads...
tar czf fitxes_uploads.tar.gz uploads/
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: No s'ha pogut comprimir uploads.
    pause
    exit /b 1
)
echo OK: fitxes_uploads.tar.gz creat

echo.
echo [3/3] Fitxers generats:
echo.
dir /b fitxes_backup.dump fitxes_uploads.tar.gz
echo.
echo ==========================================
echo  INSTRUCCIONS:
echo.
echo  1. Copia aquests 2 fitxers al servidor Ubuntu:
echo     scp fitxes_backup.dump usuari@IP_SERVIDOR:/tmp/
echo     scp fitxes_uploads.tar.gz usuari@IP_SERVIDOR:/tmp/
echo.
echo  2. Al servidor Ubuntu, executa:
echo     sudo -u postgres pg_restore -c -d fitxes_tecniques /tmp/fitxes_backup.dump
echo     sudo tar xzf /tmp/fitxes_uploads.tar.gz -C /var/www/fitxes-tecniques/backend/
echo     sudo chown -R www-data:www-data /var/www/fitxes-tecniques/backend/uploads/
echo     sudo systemctl restart fitxes-tecniques
echo ==========================================
echo.
pause
