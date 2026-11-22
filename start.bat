@echo off
rem ============================================================
rem  Odwolania2JSON - uruchamianie (Windows)
rem  Przy pierwszym starcie tworzy srodowisko i instaluje
rem  biblioteki, potem od razu odpala program.
rem ============================================================
pushd "%~dp0"

rem --- 1. Szukamy Pythona ---
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (
    where python >nul 2>nul && set PY=python
)
if not defined PY (
    echo Nie znaleziono Pythona.
    echo Zainstaluj go z python.org i zaznacz "Add python.exe to PATH".
    goto blad
)

rem --- 2. Srodowisko wirtualne (tworzone tylko raz) ---
if not exist ".venv\Scripts\python.exe" (
    echo Tworze srodowisko wirtualne...
    %PY% -m venv .venv
    if errorlevel 1 goto blad
)

rem --- 3. Biblioteki (instalowane tylko raz) ---
if not exist ".venv\zainstalowane.txt" (
    echo Instaluje biblioteki, to moze chwile potrwac...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto blad
    echo ok> ".venv\zainstalowane.txt"
)

rem --- 4. Klucz API ---
if not exist ".env" (
    echo Brak pliku .env obok main.py.
    echo Utworz go i wpisz jedna linijke: GROQ_API_KEY=twoj_klucz
    goto blad
)

rem --- 5. Start programu ---
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto blad
popd
exit /b 0

:blad
echo.
echo Cos poszlo nie tak. Przeczytaj komunikat powyzej.
pause
popd
exit /b 1