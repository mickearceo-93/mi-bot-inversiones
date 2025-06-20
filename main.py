
import os
import sys
import json
import requests
import yfinance as yf
from flask import Flask, request
from datetime import datetime
import threading
from threading import Timer

sys.stdout.reconfigure(line_buffering=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO_RAW_URL = "https://raw.githubusercontent.com/mickearceo-93/mi-bot-inversiones/main/portafolio_gbm_miguel.json"

mensajes_procesados = set()
mensajes_lock = threading.Lock()
cancelaciones_activas = {}

ticker_alias = {
    "1211 N": "BYD",
    "1810 N": "XIAOMI",
    "OXY1 *": "OXY"
}

app = Flask(__name__)

def limpiar_mensaje(msg_id, delay=60):
    def remover():
        with mensajes_lock:
            mensajes_procesados.discard(msg_id)
    Timer(delay, remover).start()

def cargar_portafolio_privado():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    response = requests.get(REPO_RAW_URL, headers=headers)
    response.raise_for_status()
    return response.json()

def obtener_analisis_openai(nombre, ticker, chat_id):
    if cancelaciones_activas.get(chat_id):
        return "⏹ Análisis cancelado por el usuario."

    prompt = (
        f"Dame un análisis financiero actualizado de {nombre} ({ticker}), "
        "incluyendo: 1. Noticias recientes relevantes, 2. Proyecciones de analistas, "
        "3. Recomendación final (comprar, vender o mantener) como si fueras un asesor financiero profesional. "
        "TODO ESTO debe ser resumido y conciso, necesito solo información útil para poder decidir rápidamente. "
        "Evita textos largos porque si no me acabaré mis tokens. "
        "Y una cosa más: la recomendación final debe ser directa y clara. Solo responde COMPRAR, VENDER o MANTENER."
    )
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"⚠️ OpenAI error {response.status_code}: {response.text[:80]}..."
    except requests.exceptions.Timeout:
        return "⚠️ Tiempo de espera agotado al solicitar análisis."

def limpiar_ticker(raw):
    try:
        return str(raw).strip().split()[0].replace("*", "").replace("$", "")
    except:
        return str(raw)

def traducir_nombre(raw):
    base = str(raw).strip().replace("*", "")
    return ticker_alias.get(base, base)

def enviar_mensaje(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    requests.post(url, json=payload)

def procesar_mensaje(datos):
    if "message" in datos:
        msg_id = datos["message"]["message_id"]
        chat_id = datos["message"]["chat"]["id"]
        texto = datos["message"].get("text", "").strip()

        with mensajes_lock:
            if msg_id in mensajes_procesados:
                print(f"⏭ Ya procesado message_id={msg_id}")
                return
            mensajes_procesados.add(msg_id)
            limpiar_mensaje(msg_id)

        if texto == "/cancelar":
            cancelaciones_activas[chat_id] = True
            enviar_mensaje(chat_id, "❌ Se ha cancelado la operación en curso.")
            return

        if texto == "/start":
            enviar_mensaje(chat_id, "👋 ¡Bienvenido Miguel! Usa /resumen para ver tu portafolio.")
            return

        if texto == "/resumen":
            cancelaciones_activas.pop(chat_id, None)
            try:
                portafolio = cargar_portafolio_privado()
                tickers_procesados = set()
                for accion in portafolio:
                    if cancelaciones_activas.get(chat_id):
                        enviar_mensaje(chat_id, "⏹ Operación cancelada.")
                        return

                    datos = {k.strip(): v for k, v in accion.items()}
                    raw_ticker = datos.get("Ticker", "")
                    ticker = limpiar_ticker(raw_ticker)
                    nombre_legible = traducir_nombre(raw_ticker)

                    if str(nombre_legible).upper() == "EFECTIVO":
                        continue
                    if str(nombre_legible).upper() == "MERCADO DE CAPITALES NACIONAL":
                        enviar_mensaje(chat_id, f"📊 {nombre_legible}")
                        continue

                    if ticker in tickers_procesados:
                        continue
                    tickers_procesados.add(ticker)

                    try:
                        compra = float(datos.get("Costo_promedio", 0) or 0)
                        actual = float(datos.get("Precio_mercado", 0) or 0)
                        titulos = int(datos.get("Titulos", 0) or 0)
                    except:
                        continue

                    if not raw_ticker or compra == 0 or actual == 0 or nombre_legible == "nan":
                        continue

                    ganancia = actual - compra
                    pct = ((ganancia) / compra) * 100

                    fechas_manual = {
                        "AAPL": "15 Ene 2025", "ABNB": "22 Feb 2025", "AMZN": "10 Ene 2025",
                        "NU": "12 Mar 2025", "NVDA": "05 Ene 2025", "OXY": "03 Jun 2025",
                        "PYPL": "19 Mar 2025", "SHOP": "07 Mar 2025", "BYD": "12 May 2025",
                        "XIAOMI": "26 May 2025", "ALSEA": "13 Ene 2025", "BBVA": "17 Ene 2025",
                        "CEMEX": "20 Feb 2025", "GFINBUR": "26 Feb 2025"
                    }
                    fecha_compra = fechas_manual.get(ticker.upper(), "No disponible")

                    if cancelaciones_activas.get(chat_id):
                        enviar_mensaje(chat_id, "⏹ Operación cancelada.")
                        return

                    analisis = obtener_analisis_openai(nombre_legible, ticker, chat_id)

                    if cancelaciones_activas.get(chat_id):
                        enviar_mensaje(chat_id, "⏹ Operación cancelada.")
                        return

                    resumen = f"📊 {nombre_legible}"
                    resumen += f"\n1. Precio de compra: ${compra:.2f}"
                    resumen += f"\n2. Fecha estimada de compra: {fecha_compra}"
                    resumen += f"\n3. Precio actual: ${actual:.2f}"
                    resumen += f"\n4. Ganancia: ${ganancia:.2f} ({pct:.2f}%)"
                    resumen += f"\n5. Títulos comprados: {titulos}"
                    resumen += f"\n6. Ganancia total estimada: ${ganancia * titulos:.2f}"
                    resumen += f"\n7. Análisis financiero:\n{analisis}"

                    enviar_mensaje(chat_id, resumen)

                cancelaciones_activas.pop(chat_id, None)

            except Exception as e:
                enviar_mensaje(chat_id, f"⚠️ Error procesando tu portafolio:\n{str(e)}")
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen o /cancelar.")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    datos = request.get_json()
    threading.Thread(target=procesar_mensaje, args=(datos,)).start()
    return {"ok": True}

@app.route('/')
def health():
    return "Bot corriendo correctamente ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
