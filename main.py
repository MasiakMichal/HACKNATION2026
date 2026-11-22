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
        self.title("Odwołania2json — Drop box")
        self.geometry("620x700")

        # lista krotek: (pelna_sciezka_pdf, sciezka_wzgledna_dla_outputu)
        self.zadania = []
        self.folder = None    # wybrany folder docelowy (np. output)

        # --- wybór folderu docelowego ---
        self.przycisk_folder = ttk.Button(
            self, text="1. Wybierz folder docelowy (output)", command=self.wybierz_folder
        )
        self.przycisk_folder.pack(pady=(15, 0))

        self.etykieta_folder = ttk.Label(self, text="Nie wybrano folderu docelowego")
        self.etykieta_folder.pack()

        # --- combobox ---
        self.wybor = tk.StringVar()
        self.combo = ttk.Combobox(
            self,
            textvariable=self.wybor,
            values=["auto", "przelew", "odwołanie", "pełnomocnictwo"],
            state="readonly",
        )
        self.combo.current(0)
        self.combo.pack(padx=15, pady=(15, 5))
        self.combo.bind("<<ComboboxSelected>>", self.po_wyborze)

        self.etykieta = ttk.Label(self, text="Wybrano: auto")
        self.etykieta.pack()

        # --- drop box ---
        self.strefa = tk.Label(
            self,
            text="Przeciągnij cały folder (np. 'dane' / 'input')\nlub pliki PDF tutaj\n\nalbo kliknij, żeby wybrać pliki PDF",
            relief="groove",
            bd=2,
            height=7,
        )
        self.strefa.pack(fill="both", expand=True, padx=15, pady=15)
        self.strefa.drop_target_register(DND_FILES)
        self.strefa.dnd_bind("<<Drop>>", self.po_upuszczeniu)
        self.strefa.bind("<Button-1>", self.wybierz_pliki)

        self.przycisk_folder_we = ttk.Button(
            self, text="Lub wybierz cały folder wejściowy...", command=self.wybierz_folder_wejsciowy
        )
        self.przycisk_folder_we.pack(pady=(0, 8))

        self.info = ttk.Label(self, text="Brak plików", wraplength=570)
        self.info.pack(pady=(0, 5))

        # --- przycisk na dole + miejsce na wynik ---
        self.przycisk = ttk.Button(self, text="2. Konwertuj wszystko", command=self.uruchom)
        self.przycisk.pack(pady=5)

        self.wynik = ttk.Label(self, text="", wraplength=570)
        self.wynik.pack(pady=(0, 15))

    def wybierz_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder = folder
            self.etykieta_folder.config(text=f"Zapis do: {folder}")

    def wybierz_folder_wejsciowy(self):
        folder_we = filedialog.askdirectory()
        if folder_we:
            self.obsluz_sciezki([folder_we])

    def po_wyborze(self, event):
        self.etykieta.config(text=f"Wybrano: {self.combo.get()}")

    def po_upuszczeniu(self, event):
        sciezki = self.tk.splitlist(event.data)
        self.obsluz_sciezki(sciezki)

    def wybierz_pliki(self, event=None):
        sciezki = filedialog.askopenfilenames(filetypes=[("Pliki PDF", "*.pdf")])
        if sciezki:
            self.obsluz_sciezki(sciezki)

    def obsluz_sciezki(self, sciezki):
        znalezione = []
        for sciezka in sciezki:
            if os.path.isdir(sciezka):
                # Przelatuje po całym drzewie podfolderów (np. przyklad_01, przyklad_02...)
                for root, _, files in os.walk(sciezka):
                    for file in sorted(files):
                        if file.lower().endswith(".pdf"):
                            pelna = os.path.join(root, file)
                            rel = os.path.relpath(pelna, sciezka)
                            znalezione.append((pelna, rel))
            elif os.path.isfile(sciezka) and sciezka.lower().endswith(".pdf"):
                znalezione.append((sciezka, os.path.basename(sciezka)))

        if not znalezione:
            self.info.config(text="Nie znaleziono plików PDF!")
            return

        self.zadania = znalezione
        if len(znalezione) == 1:
            self.info.config(text=f"Wczytano: {znalezione[0][1]}")
        else:
            przyklady = ", ".join(rel for _, rel in znalezione[:3])
            reszta = f" (+{len(znalezione) - 3} więcej)" if len(znalezione) > 3 else ""
            self.info.config(text=f"Wczytano {len(znalezione)} plików PDF: {przyklady}{reszta}")

    def uruchom(self):
        if not self.folder:
            self.wynik.config(text="Najpierw wybierz folder docelowy!")
            return

        if not self.zadania:
            self.wynik.config(text="Najpierw przeciągnij folder lub pliki PDF!")
            return

        opcja = self.combo.get()
        bot = Algorytm()
        zapisane = 0
        bledy = 0

        for idx, (sciezka_pdf, rel_path) in enumerate(self.zadania, 1):
            self.wynik.config(text=f"Przetwarzam [{idx}/{len(self.zadania)}]: {rel_path}...")
            self.update_idletasks()

            try:
                reader = PdfReader(sciezka_pdf)
                tekst = "\n".join(page.extract_text() or "" for page in reader.pages[:4])

                if len(tekst.strip()) < 40:
                    dane = {}
                else:
                    odpowiedz = bot.ask(opcja, tekst)
                    print(f"--- {rel_path} ---\n{odpowiedz}")

                    try:
                        dane = json.loads(odpowiedz)
                    except json.JSONDecodeError:
                        dane = json.loads(odpowiedz[odpowiedz.find("{"):odpowiedz.rfind("}") + 1])

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
                if idx < len(self.zadania):
                    time.sleep(0.8)

            except Exception as e:
                bledy += 1
                print(f"Błąd przy {rel_path}: {e}")

        self.wynik.config(
            text=f"Gotowe! Zapisano: {zapisane}/{len(self.zadania)} plików w {self.folder}"
            + (f" (błędy: {bledy})" if bledy else "")
        )


if __name__ == "__main__":
    Okno().mainloop()