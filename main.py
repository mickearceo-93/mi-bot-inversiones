
import os
import sys
import json
import math
import requests
from flask import Flask, request

sys.stdout.reconfigure(line_buffering=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
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

def obtener_noticias(ticker):
    url = f"https://newsapi.org/v2/everything?q={ticker}&apiKey={NEWSAPI_KEY}&pageSize=1&sortBy=publishedAt&language=es"
    response = requests.get(url)
    if response.status_code == 200:
        noticias = response.json().get("articles", [])
        if noticias:
            return f"📰 {noticias[0]['title']}"
    return "📰 Sin noticias recientes."

def obtener_proyecciones(ticker):
    url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            recomendacion = data[0]
            corto = recomendacion.get("buy", 0)
            mantener = recomendacion.get("hold", 0)
            vender = recomendacion.get("sell", 0)
            return f"Corto plazo: 🔼 {corto}, Mediano: 🤝 {mantener}, Largo: 🔽 {vender}"
    return "📉 Sin proyecciones disponibles."

def sugerencia(var_dia, pm):
    if var_dia < -3 or pm < -200:
        return "🔻 Sugerencia: VENDER"
    elif var_dia > 2 and pm > 150:
        return "🟢 Sugerencia: COMPRAR MÁS"
    else:
        return "🟡 Sugerencia: MANTENER"

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
                    accion_limpia = {k.strip(): v for k, v in accion.items()}
                    ticker = str(accion_limpia.get("Ticker", "")).strip()
                    var_dia = float(accion_limpia.get("Var_Dia", 0) or 0)
                    pm = float(accion_limpia.get("P_M", 0) or 0)
                    precio = float(accion_limpia.get("Precio_mercado", 0) or 0)
                    compra = float(accion_limpia.get("Costo_promedio", 0) or 0)

                    if any(map(math.isnan, [pm, precio, var_dia])):
                        continue

                    noticias = obtener_noticias(ticker)
                    proy = obtener_proyecciones(ticker)
                    accion_final = sugerencia(var_dia, pm)

                    resumen = f"📊 {ticker}"
                    resumen += f"1. Precio de compra: ${compra:.2f}"
                    resumen += f"2. Variación hoy: {var_dia:.2f}%"
                    resumen += f"3. Precio actual: ${precio:.2f}"
                    resumen += f"4. Ganancia/Pérdida: ${pm:.2f}"
                    resumen += f"5. {noticias}"
                    resumen += f"6. 📈 Proyecciones: {proy}"
                    resumen += f"7. {accion_final}"

                    enviar_mensaje(chat_id, resumen)
            except Exception as e:
                enviar_mensaje(chat_id, f"⚠️ Error al cargar el portafolio:{str(e)}")
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen.")
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
