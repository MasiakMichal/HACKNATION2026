import json
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from pypdf import PdfReader
from algorytm import Algorytm


def wyczysc(obj):
    """Zamienia nowe linie i wielokrotne spacje w tekstach na jedną spację."""
    if isinstance(obj, str):
        return re.sub(r"\s+", " ", obj).strip()
    if isinstance(obj, list):
        return [wyczysc(x) for x in obj]
    if isinstance(obj, dict):
        return {k: wyczysc(v) for k, v in obj.items()}
    return obj


class Okno(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Drop box")
        self.geometry("600x670")

        self.sciezka = None   # tu ląduje wczytany plik
        self.folder = None    # tu ląduje wybrany folder

        # --- wybór folderu ---
        self.przycisk_folder = ttk.Button(
            self, text="Wybierz folder", command=self.wybierz_folder
        )
        self.przycisk_folder.pack(pady=(15, 0))

        self.etykieta_folder = ttk.Label(self, text="Nie wybrano folderu")
        self.etykieta_folder.pack()

        # --- combobox ---
        self.wybor = tk.StringVar()
        self.combo = ttk.Combobox(
            self, textvariable=self.wybor,
            values=["przelew", "odwołanie", "pełnomocnictwo"],
            state="readonly",
        )
        self.combo.current(0)
        self.combo.pack(padx=15, pady=(15, 5))
        self.combo.bind("<<ComboboxSelected>>", self.po_wyborze)

        self.etykieta = ttk.Label(self, text="Wybrano: przelew")
        self.etykieta.pack()

        # --- drop box ---
        self.strefa = tk.Label(
            self, text="Przeciągnij plik tutaj\nalbo kliknij, żeby wybrać",
            relief="groove", bd=2, height=6,
        )
        self.strefa.pack(fill="both", expand=True, padx=15, pady=15)
        self.strefa.drop_target_register(DND_FILES)
        self.strefa.dnd_bind("<<Drop>>", self.po_upuszczeniu)
        self.strefa.bind("<Button-1>", self.wybierz_plik)

        self.info = ttk.Label(self, text="Brak pliku")
        self.info.pack(pady=(0, 5))

        # --- przycisk na dole + miejsce na wynik ---
        self.przycisk = ttk.Button(self, text="Konwertuj", command=self.uruchom)
        self.przycisk.pack(pady=5)

        self.wynik = ttk.Label(self, text="", wraplength=550)
        self.wynik.pack(pady=(0, 15))

    def wybierz_folder(self):
        folder = filedialog.askdirectory()
        if folder:                      # pusty tekst = kliknięto Anuluj
            self.folder = folder
            self.etykieta_folder.config(text=folder)

    def po_wyborze(self, event):
        self.etykieta.config(text=f"Wybrano: {self.combo.get()}")

    def po_upuszczeniu(self, event):
        sciezki = self.tk.splitlist(event.data)
        self.obsluz_plik(sciezki[0])

    def wybierz_plik(self, event=None):
        sciezka = filedialog.askopenfilename()
        if sciezka:
            self.obsluz_plik(sciezka)

    def obsluz_plik(self, sciezka):
        self.sciezka = sciezka
        self.info.config(text=f"Wczytano: {sciezka}")

    def uruchom(self):
        if not self.folder:
            self.wynik.config(text="Najpierw wybierz folder!")
            return

        if not self.sciezka or not self.sciezka.lower().endswith(".pdf"):
            self.wynik.config(text="Wczytaj plik pdf!")
            return

        opcja = self.combo.get()

        self.wynik.config(text="Przetwarzam...")
        self.update_idletasks()   # odświeża okno przed zapytaniem do API

        try:
            reader = PdfReader(self.sciezka)
            tekst = reader.pages[0].extract_text()

            odpowiedz = Algorytm().ask(opcja, tekst)
            print(odpowiedz)      # podgląd w terminalu, co zwrócił model

            try:
                dane = json.loads(odpowiedz)
            except json.JSONDecodeError:
                # model dodał coś wokół JSON-a, wycinamy od { do }
                dane = json.loads(odpowiedz[odpowiedz.find("{"):odpowiedz.rfind("}") + 1])

            if isinstance(dane, str):     # JSON zakodowany drugi raz
                dane = json.loads(dane)

            dane = wyczysc(dane)          # usuwa \n z tekstów
        except json.JSONDecodeError:
            self.wynik.config(text="Model nie zwrócił poprawnego JSON-a (patrz terminal)")
            return
        except Exception as e:
            self.wynik.config(text=f"Błąd: {e}")
            return

        nazwa = os.path.splitext(os.path.basename(self.sciezka))[0] + ".json"
        plik_json = os.path.join(self.folder, nazwa)

        with open(plik_json, "w", encoding="utf-8") as plik:
            json.dump(dane, plik, ensure_ascii=False, indent=2)

        self.wynik.config(text=f"Zapisano: {plik_json}")


if __name__ == "__main__":
    Okno().mainloop()