@echo off
rem Crea l'installatore di Viator per Windows.
rem Requisiti: Python 3.9+ e Inno Setup 6 (https://jrsoftware.org/isdl.php)
rem Uso: doppio clic su questo file, oppure eseguilo dal terminale.

setlocal
cd /d "%~dp0\..\.."

echo.
echo === 1/3  Installo le librerie necessarie ===
python -m pip install --upgrade -r requirements.txt pyinstaller || goto :error

for /f %%v in ('python -c "import viator; print(viator.APP_VERSION)"') do set VERSION=%%v
echo Versione: %VERSION%
python tools\write_version_info.py || goto :error

echo.
echo === 2/3  Creo il programma con PyInstaller ===
python -m PyInstaller --noconfirm --clean --windowed --name Viator ^
  --icon assets\viator.ico ^
  --version-file packaging\windows\version_info.txt ^
  main.py || goto :error

echo.
echo === 3/3  Creo l'installatore con Inno Setup ===
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo.
  echo Inno Setup 6 non trovato. Installalo da https://jrsoftware.org/isdl.php e rilancia.
  echo Il programma senza installatore e' comunque pronto in dist\Viator\Viator.exe
  goto :end
)
%ISCC% /DAppVersion=%VERSION% packaging\windows\viator.iss || goto :error

echo.
echo Fatto! L'installatore e' in dist\installer\
goto :end

:error
echo.
echo Si e' verificato un errore: controlla i messaggi qui sopra.
exit /b 1

:end
if not defined CI pause
endlocal
