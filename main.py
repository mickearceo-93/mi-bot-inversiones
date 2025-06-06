
import os
import sys
import json
import requests
import yfinance as yf
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
    response.raise_for_status()
    return response.json()

def obtener_datos_yahoo(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "precio_actual": info.get("regularMarketPrice", 0),
            "variacion_dia": info.get("regularMarketChangePercent", 0),
            "nombre": info.get("shortName", ticker)
        }
    except Exception as e:
        print(f"⚠️ Error al obtener datos de {ticker}: {str(e)}")
        return {
            "precio_actual": 0,
            "variacion_dia": 0,
            "nombre": ticker
        }

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
    print("📥 Webhook recibido:", datos)
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        texto = datos["message"].get("text", "")

        if texto == "/start":
            enviar_mensaje(chat_id, "👋 ¡Bienvenido Miguel! Usa /resumen para ver tu portafolio con datos en tiempo real.")
        elif texto == "/resumen":
            try:
                portafolio = cargar_portafolio_privado()
                resumen = "📊 Tu resumen de hoy:n\"
                for accion in portafolio:
                    accion_limpia = {k.strip(): v for k, v in accion.items()}
                    ticker = str(accion_limpia.get("Ticker", "")).strip()
                    precio_medio = float(accion_limpia.get("P_M", 0) or 0)

                    datos = obtener_datos_yahoo(ticker)
                    precio_actual = datos["precio_actual"]
                    variacion = datos["variacion_dia"]
                    nombre = datos["nombre"]
                    ganancia = precio_actual - precio_medio
                    simbolo = "📈" if ganancia >= 0 else "📉"

                    resumen += f"{simbolo} {ticker} ({nombre}): {variacion:.2f}% hoy | Precio actual: ${precio_actual:.2f} | Gan/Pérdida: ${ganancia:.2f}\n"
            except Exception as e:
                resumen = f"⚠️ Error al generar resumen:\n{str(e)}"
            print("📄 Resumen generado:\n", resumen)
            enviar_mensaje(chat_id, resumen)
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen.")
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
