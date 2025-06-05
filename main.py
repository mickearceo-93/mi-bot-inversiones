
import os
import json
import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")  # Asegúrate de tenerlo configurado en Render
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Tu token de GitHub privado
REPO_RAW_URL = "https://raw.githubusercontent.com/mickearceo-93/mi-bot-inversiones/main/portafolio_gbm_miguel.json"

app = Flask(__name__)

def cargar_portafolio_privado():
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(REPO_RAW_URL, headers=headers)
    response.raise_for_status()
    return response.json()

def enviar_mensaje(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto
    }
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
            resumen = "📊 Aquí va tu resumen de hoy:"
"
            try:
                portafolio = cargar_portafolio_privado()
                for accion in portafolio:
                    ticker = accion["Ticker"]
                    var_dia = accion["Var_Dia"]
                    pm = accion["P_M"]
                    simbolo = "📈" if var_dia >= 0 else "📉"
                    resumen += f"{simbolo} {ticker}: {var_dia:.2f}% hoy | Gan/Pérdida: ${pm:.2f}\n"
            except Exception as e:
                resumen = f"⚠️ Error al cargar el portafolio: {str(e)}"

            enviar_mensaje(chat_id, resumen)
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen.")
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"
