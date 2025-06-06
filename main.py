import os
import sys
import json
import requests
import yfinance as yf
from flask import Flask, request
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO_RAW_URL = "https://raw.githubusercontent.com/mickearceo-93/mi-bot-inversiones/main/portafolio_gbm_miguel.json"

tickers_procesados = set()
app = Flask(__name__)

def cargar_portafolio_privado():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    response = requests.get(REPO_RAW_URL, headers=headers)
    response.raise_for_status()
    return response.json()

def estimar_fecha_compra(ticker, precio_compra):
    try:
        hist = yf.Ticker(ticker).history(period="5y")
        hist = hist[hist.index >= "2025-01-01"]
        hist = hist.dropna(subset=["Close"])
        closest = hist.iloc[(hist["Close"] - precio_compra).abs().argsort()[:1]]
        if not closest.empty:
            return closest.index[0].strftime("%d %b %Y")
    except:
        return "No disponible"
    return "No disponible"

def obtener_analisis_openai(nombre, ticker):
    prompt = (
        f"Dame un análisis financiero actualizado de {nombre} ({ticker}), "
        "incluyendo: 1. Noticias recientes relevantes, 2. Proyecciones de analistas, "
        "3. Recomendación final (comprar, vender o mantener) como si fueras un asesor financiero profesional."
        "todo esto que sea resumido y conciso neceisto solo informacion util para poder responder facilmente"
        "evita poner mucha informacion porque si no me acabare mis tokens, y una cosa más la recomendacion final"
        "que solo sea directa sin tanto cuento, solo pones o vender o manter o comprar"
    )
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"⚠️ Error OpenAI {response.status_code}: {response.text[:100]}..."

def limpiar_ticker(raw):
    return raw.strip().split()[0].replace("*", "").replace("$", "")

def enviar_mensaje(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    requests.post(url, json=payload)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    datos = request.get_json()
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        texto = datos["message"].get("text", "").strip()
        if texto == "/start":
            enviar_mensaje(chat_id, "👋 ¡Bienvenido Miguel! Usa /resumen para ver tu portafolio.")
        elif texto == "/resumen":
            try:
                portafolio = cargar_portafolio_privado()
                tickers_procesados.clear()
                for accion in portafolio:
                    datos = {k.strip(): v for k, v in accion.items()}
                    raw_ticker = datos.get("Ticker", "")
                    nombre = raw_ticker
                    ticker = limpiar_ticker(raw_ticker)
                    if ticker in tickers_procesados:
                        continue
                    tickers_procesados.add(ticker)
                    compra = float(datos.get("Costo_promedio", 0) or 0)
                    actual = float(datos.get("Precio_mercado", 0) or 0)
                    if not raw_ticker or compra == 0 or actual == 0:
                        continue
                    ganancia = actual - compra
                    pct = ((ganancia) / compra) * 100
                    fecha_compra = estimar_fecha_compra(ticker, compra)
                    analisis = obtener_analisis_openai(nombre, ticker)
                    resumen = f"📊 {nombre}\n"
                    resumen += f"1. Precio de compra: ${compra:.2f}\n"
                    resumen += f"2. Fecha estimada de compra: {fecha_compra}\n"
                    resumen += f"3. Precio actual: ${actual:.2f}\n"
                    resumen += f"4. Ganancia: ${ganancia:.2f} ({pct:.2f}%)\n"
                    resumen += f"5. Noticias y Recomendaciones: {analisis}"
                    enviar_mensaje(chat_id, resumen)
            except Exception as e:
                enviar_mensaje(chat_id, f"⚠️ Error procesando tu portafolio:\n{str(e)}")
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen.")
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
