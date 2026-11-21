import tkinter as tk
from tkinter import ttk, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from pypdf import PdfReader


class Okno(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Drop box")
        self.geometry("600x670")
        
        self.sciezka = None   # tu ląduje wczytany plik
        self.folder = None

        # --- NOWE: wybór folderu ---
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
            values=["przelew", "gotówka", "karta"],
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

        self.wynik = ttk.Label(self, text="")
        self.wynik.pack(pady=(0, 15))

    # NOWE: metoda wyboru folderu
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
        if not self.sciezka or self.sciezka[-3:] != "pdf"  :
            self.wynik.config(text=" wczytaj plik pdf!")
            return

        opcja = self.combo.get()

        # TODO: tu podepniesz swoją logikę, np.:
        # rezultat = twoja_funkcja(self.sciezka, opcja)
        reader = PdfReader(self.sciezka)
        page = reader.pages[0]
        
        rezultat = f"(placeholder) plik: {self.sciezka}, opcja: {opcja}"

        self.wynik.config(text=rezultat)
        dane_dla_algorytmu=[opcja,page.extract_text()]

        with open("test.txt","a") as f:
            f.write(page.extract_text())


if __name__ == "__main__":
    Okno().mainloop()