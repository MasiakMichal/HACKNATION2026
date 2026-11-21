import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class Algorytm:
    def __init__(self, api_key=None):
        self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.model = "qwen/qwen3.8-27b"

    def ask(self, opcja, tekst):
        # .read() zwraca ZAWARTOŚĆ pliku (wcześniej było tylko "f")
        with open("rozkaz.txt", "r", encoding="utf-8") as f:
            rozkaz = f.read()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{rozkaz}\n\n"
                        f"Wybrana opcja: {opcja}\n"
                        "Zwróć wyłącznie poprawny kod JSON, bez komentarzy "
                        "i bez bloków ```."
                    ),
                },
                {"role": "user", "content": tekst},
            ],
        )

        odpowiedz = response.choices[0].message.content
        # usuwa ewentualne "myślenie" modelu w tagach <think>...</think>
        return re.sub(r"<think>.*?</think>", "", odpowiedz, flags=re.DOTALL).strip()