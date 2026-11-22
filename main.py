import json
import os
import re
import time
import tkinter as tk
from tkinter import ttk, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from pypdf import PdfReader
from algorytm import Algorytm


POWODY_KIO = {
    1: "Decyzja o odrzuceniu oferty",
    2: "Ogłoszenie wyboru oferty",
    3: "Decyzja o wykluczeniu wykonawcy",
    4: "Publikacja specyfikacji warunków zamówienia (SWZ)",
    5: "Modyfikacja treści SWZ",
    6: "Odpowiedzi/wyjaśnienia do SWZ",
    7: "Zaniechanie odrzucenia oferty",
    8: "Zaniechanie wykluczenia wykonawcy",
    9: "Decyzja o unieważnieniu postępowania",
    10: "Zaniechanie unieważnienia postępowania",
    11: "Opis przedmiotu zamówienia (OPZ)",
    12: "Inna czynność lub zaniechanie Zamawiającego",
}


def wyczysc(obj):
    """Zamienia nowe linie i wielokrotne spacje w tekstach na jedną spację."""
    if isinstance(obj, str):
        return re.sub(r"\s+", " ", obj).strip()
    if isinstance(obj, list):
        return [wyczysc(x) for x in obj]
    if isinstance(obj, dict):
        return {k: wyczysc(v) for k, v in obj.items()}
    return obj


def napraw_formaty(opcja, dane):
    """Doczyszcza numery kont, TED, BZP, PESEL, tytuły zawodowe oraz spójność powodów KIO."""
    def bez_tytulow(txt):
        if not isinstance(txt, str):
            return txt
        txt = re.sub(
            r"(?:^|\s)(?:adw\.?|r\.\s*pr\.?|radca\s+prawny|adwokat|mec\.?|dr|mgr)(?=\s|$|,)",
            " ",
            txt,
            flags=re.I,
        )
        return re.sub(r"\s+", " ", txt).strip(" ,")

    if opcja == "przelew" and isinstance(dane.get("przelew_bankowy"), dict):
        p = dane["przelew_bankowy"]
        for k in ("z_rachunku", "na_rachunek"):
            if p.get(k):
                cyfry = re.sub(r"\D", "", str(p[k]))
                if len(cyfry) == 26:
                    p[k] = cyfry
        if isinstance(p.get("kwota"), str):
            kw = re.sub(r"[^\d,\.]", "", p["kwota"]).replace(",", ".")
            p["kwota"] = float(kw) if kw else None

    elif opcja == "odwołanie":
        kio = dane.get("OdwolanieKIO", {})
        if isinstance(kio, dict):
            pid = kio.get("czynnosc_powod_id")
            if isinstance(pid, int) and pid in POWODY_KIO:
                kio["czynnosc_opis"] = POWODY_KIO[pid]

        for odw in dane.get("Odwolujacy", []):
            if isinstance(odw.get("pelnomocnik"), dict) and odw["pelnomocnik"].get("imie_nazwisko"):
                odw["pelnomocnik"]["imie_nazwisko"] = bez_tytulow(
                    odw["pelnomocnik"]["imie_nazwisko"]
                )

        zp = dane.get("ZamowieniePubliczne", {})
        if isinstance(zp, dict):
            if zp.get("numer_ted"):
                m = re.search(r"(\d{4})/S\s*\d+\s*[-–]\s*(\d+)", str(zp["numer_ted"]), re.I)
                if m:
                    zp["numer_ted"] = f"{m.group(2)}-{m.group(1)}"
            if zp.get("numer_bzp"):
                zp["numer_bzp"] = re.sub(r"\s+", "", str(zp["numer_bzp"]))

    elif opcja == "pełnomocnictwo":
        for pel in dane.get("pelnomocnicy", []):
            if pel.get("imie_nazwisko"):
                pel["imie_nazwisko"] = bez_tytulow(pel["imie_nazwisko"])
            if pel.get("pesel") is not None:
                cyfry = re.sub(r"\D", "", str(pel["pesel"]))
                pel["pesel"] = int(cyfry) if len(cyfry) == 11 else None

    return dane



class Okno(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("Odwołania2JSON")
        self.geometry("1180x820")
        self.minsize(950, 650)
        self.configure(bg="#0b1020")

        # Te same dane, których używała poprzednia wersja.
        self.zadania = []
        self.folder = None

        self.ustaw_wyglad()
        self.zbuduj_okno()

    def ustaw_wyglad(self):
        """Ustawia kolory elementów Tkinter."""
        styl = ttk.Style(self)
        styl.theme_use("clam")

        styl.configure(
            "TCombobox",
            fieldbackground="#202744",
            background="#202744",
            foreground="#ffffff",
            arrowcolor="#c7a7ff",
            padding=8,
        )
        styl.map(
            "TCombobox",
            fieldbackground=[("readonly", "#202744")],
            foreground=[("readonly", "#ffffff")],
        )

        styl.configure(
            "Treeview",
            background="#121a30",
            fieldbackground="#121a30",
            foreground="#edf0ff",
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        styl.configure(
            "Treeview.Heading",
            background="#202744",
            foreground="#dfe3ff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=9,
        )
        styl.map(
            "Treeview",
            background=[("selected", "#493078")],
            foreground=[("selected", "#ffffff")],
        )

        styl.configure(
            "Konwersja.Horizontal.TProgressbar",
            troughcolor="#252d49",
            background="#9b68ef",
            bordercolor="#252d49",
            lightcolor="#9b68ef",
            darkcolor="#9b68ef",
        )

    def zrob_przycisk(self, rodzic, tekst, polecenie, glowny=False):
        """Tworzy kolorowy przycisk, który działa na Windows i macOS."""
        kolor = "#713bd0" if glowny else "#252d49"
        hover = "#8550e6" if glowny else "#343e60"

        przycisk = tk.Label(
            rodzic,
            text=tekst,
            bg=kolor,
            fg="white",
            padx=16,
            pady=10,
            cursor="hand2",
            font=("Segoe UI", 10, "bold" if glowny else "normal"),
        )
        przycisk.polecenie = polecenie
        przycisk.kolor = kolor
        przycisk.hover = hover
        przycisk.aktywny = True

        def kliknij(event=None):
            if przycisk.aktywny:
                przycisk.polecenie()

        def najedz(event=None):
            if przycisk.aktywny:
                przycisk.config(bg=przycisk.hover)

        def zjedz(event=None):
            if przycisk.aktywny:
                przycisk.config(bg=przycisk.kolor)

        def ustaw_stan(state):
            przycisk.aktywny = state != "disabled"
            if przycisk.aktywny:
                przycisk.config(bg=przycisk.kolor, fg="white", cursor="hand2")
            else:
                przycisk.config(bg="#30364d", fg="#8d94ac", cursor="arrow")

        # Zachowujemy wygodne wywołanie .config(state=...), używane przez program.
        przycisk.ustaw_stan = ustaw_stan
        przycisk.bind("<Button-1>", kliknij)
        przycisk.bind("<Enter>", najedz)
        przycisk.bind("<Leave>", zjedz)

        return przycisk

    def zbuduj_okno(self):
        """Buduje nowy wygląd aplikacji. Obsługa konwersji pozostaje osobno."""

        glowny = tk.Frame(self, bg="#0b1020")
        glowny.pack(fill="both", expand=True)

        # Lewy panel.
        lewy = tk.Frame(glowny, bg="#11172b", width=220)
        lewy.pack(side="left", fill="y")
        lewy.pack_propagate(False)

        tk.Label(
            lewy,
            text="▣  Odwołania2JSON",
            bg="#11172b",
            fg="white",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=20, pady=(28, 4))

        tk.Label(
            lewy,
            text="KONWERTER PDF → JSON",
            bg="#11172b",
            fg="#a99acb",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=22)

        tk.Frame(lewy, bg="#29314d", height=1).pack(fill="x", padx=18, pady=25)

        tk.Label(
            lewy,
            text="  ◉   Konwersja",
            bg="#39245f",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=12,
            anchor="w",
        ).pack(fill="x", padx=10)

        tk.Label(
            lewy,
            text="PDF  →  { }",
            bg="#171f39",
            fg="#c8aaff",
            font=("Segoe UI", 22, "bold"),
            pady=22,
        ).pack(side="bottom", fill="x", padx=16, pady=(0, 5))

        tk.Label(
            lewy,
            text="Dodaj dokumenty PDF,\na program zapisze je\njako pliki JSON.",
            bg="#11172b",
            fg="#aeb8d5",
            font=("Segoe UI", 10),
            justify="center",
        ).pack(side="bottom", fill="x", padx=12, pady=(0, 25))

        # Główna część okna.
        prawa = tk.Frame(glowny, bg="#0b1020")
        prawa.pack(side="left", fill="both", expand=True, padx=28, pady=22)

        tk.Label(
            prawa,
            text="Zamiana PDF na JSON",
            bg="#0b1020",
            fg="#f4f5ff",
            font=("Segoe UI", 25, "bold"),
        ).pack(anchor="w")

        tk.Label(
            prawa,
            text="Dodaj dokumenty, wybierz ich rodzaj i rozpocznij konwersję.",
            bg="#0b1020",
            fg="#aab2ce",
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(5, 18))

        # Wybór folderu zapisu i rodzaju dokumentu.
        ustawienia = tk.Frame(prawa, bg="#0b1020")
        ustawienia.pack(fill="x", pady=(0, 15))
        ustawienia.columnconfigure(0, weight=1)
        ustawienia.columnconfigure(1, weight=1)

        karta_folder = tk.Frame(
            ustawienia, bg="#171f37", highlightbackground="#303b5c", highlightthickness=1
        )
        karta_folder.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            karta_folder,
            text="Folder, w którym zapiszą się pliki JSON",
            bg="#171f37",
            fg="#f0f1ff",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 5))

        wiersz_folder = tk.Frame(karta_folder, bg="#171f37")
        wiersz_folder.pack(fill="x", padx=14, pady=(0, 12))

        self.etykieta_folder = tk.Label(
            wiersz_folder,
            text="Nie wybrano folderu",
            bg="#171f37",
            fg="#aab2ce",
            anchor="w",
            wraplength=270,
        )
        self.etykieta_folder.pack(side="left", fill="x", expand=True)

        self.przycisk_folder = self.zrob_przycisk(
            wiersz_folder, "Wybierz", self.wybierz_folder
        )
        self.przycisk_folder.pack(side="right", padx=(8, 0))

        karta_tryb = tk.Frame(
            ustawienia, bg="#171f37", highlightbackground="#303b5c", highlightthickness=1
        )
        karta_tryb.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(
            karta_tryb,
            text="Rodzaj dokumentu",
            bg="#171f37",
            fg="#f0f1ff",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 5))

        self.wybor = tk.StringVar()
        self.combo = ttk.Combobox(
            karta_tryb,
            textvariable=self.wybor,
            values=["auto", "przelew", "odwołanie", "pełnomocnictwo"],
            state="readonly",
        )
        self.combo.current(0)
        self.combo.pack(fill="x", padx=14, pady=(0, 12))
        self.combo.bind("<<ComboboxSelected>>", self.po_wyborze)

        # Duże pole dodawania dokumentów.
        self.strefa = tk.Frame(
            prawa,
            bg="#17152f",
            highlightbackground="#9863e8",
            highlightthickness=2,
            height=155,
        )
        self.strefa.pack(fill="x", pady=(0, 14))
        self.strefa.pack_propagate(False)

        tk.Label(
            self.strefa,
            text="⇧",
            bg="#17152f",
            fg="#c29aff",
            font=("Segoe UI", 31, "bold"),
        ).pack(pady=(10, 0))

        tk.Label(
            self.strefa,
            text="Przeciągnij tutaj pliki PDF lub cały folder",
            bg="#17152f",
            fg="#f4f2ff",
            font=("Segoe UI", 14, "bold"),
        ).pack()

        tk.Label(
            self.strefa,
            text="albo wybierz dokumenty z komputera",
            bg="#17152f",
            fg="#b4b5d2",
            font=("Segoe UI", 10),
        ).pack(pady=(3, 8))

        self.strefa.drop_target_register(DND_FILES)
        self.strefa.dnd_bind("<<Drop>>", self.po_upuszczeniu)
        self.strefa.bind("<Button-1>", self.wybierz_pliki)

        for element in self.strefa.winfo_children():
            element.bind("<Button-1>", self.wybierz_pliki)

        przyciski = tk.Frame(prawa, bg="#0b1020")
        przyciski.pack(fill="x", pady=(0, 17))

        self.przycisk_pliki = self.zrob_przycisk(
            przyciski, "+  Wybierz pliki PDF", self.wybierz_pliki, glowny=True
        )
        self.przycisk_pliki.pack(side="left")

        self.przycisk_folder_we = self.zrob_przycisk(
            przyciski, "Wybierz cały folder", self.wybierz_folder_wejsciowy
        )
        self.przycisk_folder_we.pack(side="left", padx=9)

        # Pasek postępu i przycisk konwersji.
        dol = tk.Frame(
            prawa, bg="#171f37", highlightbackground="#303b5c", highlightthickness=1
        )
        dol.pack(side="bottom", fill="x", pady=(16, 0))

        lewa_dol = tk.Frame(dol, bg="#171f37")
        lewa_dol.pack(side="left", fill="both", expand=True, padx=15, pady=12)

        self.wynik = tk.Label(
            lewa_dol,
            text="Dodaj pliki PDF, aby rozpocząć.",
            bg="#171f37",
            fg="#e9eaff",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.wynik.pack(fill="x")

        self.pasek = ttk.Progressbar(
            lewa_dol,
            style="Konwersja.Horizontal.TProgressbar",
            mode="determinate",
            maximum=100,
        )
        self.pasek.pack(fill="x", pady=(9, 0))

        self.przycisk = self.zrob_przycisk(
            dol, "▶  Konwertuj", self.uruchom, glowny=True
        )
        self.przycisk.pack(side="right", padx=15, pady=14)


        # Lista dodanych dokumentów.
        naglowek_listy = tk.Frame(prawa, bg="#0b1020")
        naglowek_listy.pack(fill="x", pady=(0, 8))

        self.liczba_plikow = tk.Label(
            naglowek_listy,
            text="Pliki do konwersji (0)",
            bg="#0b1020",
            fg="#f3f4ff",
            font=("Segoe UI", 14, "bold"),
        )
        self.liczba_plikow.pack(side="left")

        self.przycisk_wyczysc = self.zrob_przycisk(
            naglowek_listy, "Wyczyść listę", self.wyczysc_liste
        )
        self.przycisk_wyczysc.pack(side="right")

        tabela_frame = tk.Frame(prawa, bg="#171f37")
        tabela_frame.pack(fill="both", expand=True, side="top")

        self.tabela = ttk.Treeview(
            tabela_frame,
            columns=("plik", "status"),
            show="headings",
            height=7,
        )
        self.tabela.heading("plik", text="Nazwa pliku")
        self.tabela.heading("status", text="Stan")
        self.tabela.column("plik", width=580, anchor="w")
        self.tabela.column("status", width=150, anchor="center")
        self.tabela.pack(fill="both", expand=True, padx=1, pady=1)


    def wybierz_folder(self):
        folder = filedialog.askdirectory()

        if folder:
            self.folder = folder
            self.etykieta_folder.config(text=folder)

    def wybierz_folder_wejsciowy(self):
        folder_we = filedialog.askdirectory()

        if folder_we:
            self.obsluz_sciezki([folder_we])

    def po_wyborze(self, event):
        self.wynik.config(text=f"Wybrano rodzaj dokumentu: {self.combo.get()}")

    def po_upuszczeniu(self, event):
        sciezki = self.tk.splitlist(event.data)
        self.obsluz_sciezki(sciezki)

    def wybierz_pliki(self, event=None):
        sciezki = filedialog.askopenfilenames(
            filetypes=[("Pliki PDF", "*.pdf")]
        )

        if sciezki:
            self.obsluz_sciezki(sciezki)

    def obsluz_sciezki(self, sciezki):
        # Ta część działa tak samo jak w Twoim oryginalnym kodzie.
        znalezione = []

        for sciezka in sciezki:
            if os.path.isdir(sciezka):
                for root, _, files in os.walk(sciezka):
                    for file in sorted(files):
                        if file.lower().endswith(".pdf"):
                            pelna = os.path.join(root, file)
                            rel = os.path.relpath(pelna, sciezka)
                            znalezione.append((pelna, rel))

            elif os.path.isfile(sciezka) and sciezka.lower().endswith(".pdf"):
                znalezione.append((sciezka, os.path.basename(sciezka)))

        if not znalezione:
            self.wynik.config(text="Nie znaleziono plików PDF.")
            return

        self.zadania = znalezione
        self.odswiez_liste()

        if len(znalezione) == 1:
            self.wynik.config(text=f"Dodano: {znalezione[0][1]}")
        else:
            self.wynik.config(text=f"Dodano plików PDF: {len(znalezione)}")

    def odswiez_liste(self):
        """Odświeża listę plików w oknie."""
        for element in self.tabela.get_children():
            self.tabela.delete(element)

        for sciezka, rel_path in self.zadania:
            self.tabela.insert(
                "",
                "end",
                values=(rel_path, "Czeka"),
            )

        self.liczba_plikow.config(
            text=f"Pliki do konwersji ({len(self.zadania)})"
        )
        self.pasek["value"] = 0

    def wyczysc_liste(self):
        self.zadania = []
        self.odswiez_liste()
        self.wynik.config(text="Lista jest pusta.")

    def ustaw_stan_pliku(self, indeks, stan):
        """Zmienia stan pliku na liście."""
        elementy = self.tabela.get_children()

        if indeks < len(elementy):
            wartosci = list(self.tabela.item(elementy[indeks], "values"))
            wartosci[1] = stan
            self.tabela.item(elementy[indeks], values=wartosci)

    def uruchom(self):
        if not self.folder:
            self.wynik.config(text="Najpierw wybierz folder docelowy.")
            return

        if not self.zadania:
            self.wynik.config(text="Najpierw dodaj pliki PDF.")
            return

        opcja = self.combo.get()
        bot = Algorytm()
        zapisane = 0
        bledy = 0

        self.przycisk.ustaw_stan("disabled")
        self.pasek["value"] = 0

        # Poniższa część konwersji zachowuje działanie z Twojego kodu.
        for idx, (sciezka_pdf, rel_path) in enumerate(self.zadania, 1):
            self.wynik.config(
                text=f"Przetwarzam {idx}/{len(self.zadania)}: {rel_path}"
            )
            self.ustaw_stan_pliku(idx - 1, "Przetwarzanie…")
            self.update_idletasks()

            try:
                reader = PdfReader(sciezka_pdf)
                tekst = "\n".join(
                    page.extract_text() or ""
                    for page in reader.pages[:4]
                )

                if len(tekst.strip()) < 40:
                    dane = {}
                else:
                    odpowiedz = bot.ask(opcja, tekst)
                    print(f"--- {rel_path} ---\n{odpowiedz}")

                    try:
                        dane = json.loads(odpowiedz)
                    except json.JSONDecodeError:
                        dane = json.loads(
                            odpowiedz[
                                odpowiedz.find("{"):odpowiedz.rfind("}") + 1
                            ]
                        )

                    if isinstance(dane, str):
                        dane = json.loads(dane)

                    if isinstance(dane, dict) and dane:
                        dane = wyczysc(dane)
                        typ_do_naprawy = opcja

                        if opcja == "auto":
                            if "przelew_bankowy" in dane:
                                typ_do_naprawy = "przelew"
                            elif "mocodawca" in dane:
                                typ_do_naprawy = "pełnomocnictwo"
                            elif "OdwolanieKIO" in dane:
                                typ_do_naprawy = "odwołanie"

                        dane = napraw_formaty(typ_do_naprawy, dane)
                    else:
                        dane = {}

                sciezka_json = os.path.join(
                    self.folder, os.path.splitext(rel_path)[0] + ".json"
                )
                os.makedirs(os.path.dirname(sciezka_json), exist_ok=True)

                with open(sciezka_json, "w", encoding="utf-8") as plik:
                    json.dump(dane, plik, ensure_ascii=False, indent=2)

                zapisane += 1
                self.ustaw_stan_pliku(idx - 1, "Gotowe")

                if idx < len(self.zadania):
                    time.sleep(0.8)

            except Exception as e:
                bledy += 1
                self.ustaw_stan_pliku(idx - 1, "Błąd")
                print(f"Błąd przy {rel_path}: {e}")

            self.pasek["value"] = idx / len(self.zadania) * 100
            self.update_idletasks()

        self.przycisk.ustaw_stan("normal")
        self.wynik.config(
            text=f"Gotowe! Zapisano: {zapisane}/{len(self.zadania)} plików. Błędy: {bledy}."
        )


if __name__ == "__main__":
    Okno().mainloop()
