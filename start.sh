#!/usr/bin/env bash
# Odwolania2JSON - uruchamianie w WSL / Linuksie
cd "$(dirname "$0")" || exit 1

# 1. Tkinter (nie instaluje sie przez pip)
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Brak Tkintera. Zainstaluj: sudo apt install python3-tk"
    exit 1
fi

# 2. Srodowisko wirtualne (tworzone tylko raz)
if [ ! -x .venv/bin/python ]; then
    echo "Tworze srodowisko wirtualne..."
    python3 -m venv .venv || { echo "Zainstaluj: sudo apt install python3-venv"; exit 1; }
fi

# 3. Biblioteki (instalowane tylko raz)
if [ ! -f .venv/.zainstalowane ]; then
    echo "Instaluje biblioteki..."
    .venv/bin/python -m pip install -r requirements.txt || exit 1
    touch .venv/.zainstalowane
fi

# 4. Klucz API
if [ ! -f .env ]; then
    echo "Brak pliku .env obok main.py."
    echo "Utworz go i wpisz jedna linijke: GROQ_API_KEY=twoj_klucz"
    exit 1
fi

# 5. Start programu
exec .venv/bin/python main.py