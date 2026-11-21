import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class Algorytm:
    def __init__(self, api_key=None):
        self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.model = "qwen/qwen3.8-27b"

    def ask(self, question):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Jesteś pomocnym asystentem AI. Odpowiadasz po polsku."
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        return response.choices[0].message.content


# Klucz pobierze się automatycznie z pliku .env
bot = Algorytm()

# Pytanie do Algorytmu
answer = bot.ask("Cześć! Co potrafisz?")

print(answer)