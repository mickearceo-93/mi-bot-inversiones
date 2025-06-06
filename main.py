
import os
import sys
import json
import requests
from flask import Flask, request

sys.stdout.reconfigure(line_buffering=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_RAW_URL = "https://raw.githubusercontent.com/mickearceo-93/mi-bot-inversiones/main/portafolio_gbm_miguel.json"

app = Flask(__name__)

def cargar_portafolio_privado():
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(REPO_RAW_URL, headers=headers)
    print("🔍 GitHub response code:", response.status_code)
    print("🔍 GitHub response text (start):", response.text[:150])
    response.raise_for_status()
    return response.json()

def enviar_mensaje(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto
    }
    print("📤 Enviando mensaje:", payload)
    requests.post(url, json=payload)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    datos = request.get_json()
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        texto = datos["message"].get("text", "")

        if texto == "/start":
            enviar_mensaje(chat_id, "👋 ¡Bienvenido Miguel! Usa /resumen para ver tu portafolio.")
        elif texto == "/resumen":
            try:
                portafolio = cargar_portafolio_privado()
                resumen = "📊 Tu resumen de hoy:\n"
                for accion in portafolio:
                    accion_limpia = {k.strip(): v for k, v in accion.items()}
                    ticker = str(accion_limpia.get("Ticker", "")).strip()
                    var_dia = float(accion_limpia.get("Var_Dia", 0) or 0)
                    pm = float(accion_limpia.get("P_M", 0) or 0)
                    simbolo = "📈" if var_dia >= 0 else "📉"
                    resumen += f"{simbolo} {ticker}: {var_dia:.2f}% hoy | Gan/Pérdida: ${pm:.2f}\n"
            except Exception as e:
                resumen = f"⚠️ Error al cargar el portafolio:\n{str(e)}"

            print("📄 Resumen generado:\n", resumen)
            enviar_mensaje(chat_id, resumen)
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen.")
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"
