
import os
import sys
import json
import math
import requests
import yfinance as yf
from flask import Flask, request
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_RAW_URL = "https://raw.githubusercontent.com/mickearceo-93/mi-bot-inversiones/main/portafolio_gbm_miguel.json"

app = Flask(__name__)

# Mapeo personalizado de tickers y nombres
TICKER_MAP = {
    "1211 N": ("1211.HK", "BYD"),
    "1810 N": ("1810.HK", "Xiaomi"),
    "SHOP N": ("SHOP", "Shopify"),
    "PYPL *": ("PYPL", "PayPal"),
    "AMZN *": ("AMZN", "Amazon"),
    "AAPL *": ("AAPL", "Apple"),
    "ABNB *": ("ABNB", "Airbnb"),
    "NVDA *": ("NVDA", "Nvidia"),
    "OXY1 *": ("OXY", "Occidental Petroleum"),
    "NU N": ("NU", "Nu Holdings"),
    "BBVA *": ("BBVA.MX", "BBVA"),
    "CEMEX CPO": ("CEMEXCPO.MX", "Cemex"),
    "GFINBUR O": ("GFINBURO.MX", "Inbursa"),
    "ALSEA *": ("ALSEA.MX", "Alsea")
}

def cargar_portafolio_privado():
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
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

def obtener_noticia_relevante(ticker):
    try:
        news = yf.Ticker(ticker).news
        if news:
            return "📰 " + news[0]["title"]
    except:
        pass
    return "📰 Sin noticias disponibles"

def obtener_proyecciones(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        recs = tk.recommendations
        corto, mediano, largo = "🤝", "🤝", "🤝"

        if recs is not None and not recs.empty:
            ultimos = recs.tail(5)["To Grade"].value_counts()
            if "Buy" in ultimos:
                corto = "🔼"
            if "Hold" in ultimos:
                mediano = "🤝"
            if "Sell" in ultimos:
                largo = "🔽"

        target = info.get("targetMeanPrice", None)
        if target:
            return f"C: {corto}, M: {mediano}, L: {largo} | Objetivo: ${target:.2f}"
    except:
        return "📉 Proyecciones no disponibles"
    return "📉 Proyecciones no disponibles"

def sugerencia(pct):
    if pct < -10:
        return "🔻 Sugerencia: VENDER"
    elif pct > 10:
        return "🟢 Sugerencia: COMPRAR MÁS"
    else:
        return "🟡 Sugerencia: MANTENER"

def limpiar_ticker(raw_ticker):
    base = str(raw_ticker).strip().replace("$", "").replace("*", "")
    return base.split()[0]

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
            try:
                portafolio = cargar_portafolio_privado()
                for accion in portafolio:
                    datos = {k.strip(): v for k, v in accion.items()}
                    raw_ticker = datos.get("Ticker", "")
                    compra = float(datos.get("Costo_promedio", 0) or 0)
                    actual = float(datos.get("Precio_mercado", 0) or 0)

                    if not raw_ticker or compra == 0 or actual == 0:
                        continue

                    if raw_ticker in TICKER_MAP:
                        ticker, nombre = TICKER_MAP[raw_ticker]
                    else:
                        ticker = limpiar_ticker(raw_ticker)
                        nombre = ticker

                    try:
                        info = yf.Ticker(ticker).info
                        if not info or not info.get("regularMarketPrice"):
                            enviar_mensaje(chat_id, f"⚠️ No se encontró información para {raw_ticker}")
                            continue
                    except:
                        enviar_mensaje(chat_id, f"⚠️ No se pudo procesar {raw_ticker}")
                        continue

                    ganancia = actual - compra
                    pct = ((ganancia) / compra) * 100
                    fecha_compra = estimar_fecha_compra(ticker, compra)
                    noticia = obtener_noticia_relevante(ticker)
                    proy = obtener_proyecciones(ticker)
                    accion_final = sugerencia(pct)

                    resumen = f"📊 {nombre}\n"
                    resumen += f"1. Precio de compra: ${compra:.2f}\n"
                    resumen += f"2. Fecha estimada de compra: {fecha_compra}\n"
                    resumen += f"3. Precio actual: ${actual:.2f}\n"
                    resumen += f"4. Ganancia: ${ganancia:.2f} ({pct:.2f}%)\n"
                    resumen += f"5. {noticia}\n"
                    resumen += f"6. 📈 Proyecciones: {proy}\n"
                    resumen += f"7. {accion_final}"

                    enviar_mensaje(chat_id, resumen)
            except Exception as e:
                enviar_mensaje(chat_id, f"⚠️ Error al cargar el portafolio:\n{str(e)}")
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen.")
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
