
import os
import json
from flask import Flask, request
import math

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "debug_token")

def enviar_mensaje(chat_id, texto):
    print(f"[MENSAJE A {chat_id}]\n{texto}\n")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    datos = request.get_json()
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        texto = datos["message"].get("text", "").strip()

        if texto == "/resumen":
            portafolio = obtener_portafolio_simulado()
            for accion in portafolio:
                datos = {k.strip(): v for k, v in accion.items()}
                nombre_legible = datos.get("Nombre", "").strip().upper()
                if nombre_legible in ["EFECTIVO", "NAN", ""] or "EFECTIVO" in nombre_legible:
                    continue
                try:
                    compra = float(datos.get("Costo_promedio", 0) or 0)
                    actual = float(datos.get("Precio_mercado", 0) or 0)
                    if compra == 0 or actual == 0:
                        resumen = f"📊 {nombre_legible}\n1. Precio de compra: no disponible\n2. Precio actual: no disponible\n3. Estado: ⚠️ Sin datos de precio"
                        enviar_mensaje(chat_id, resumen)
                        continue
                    ganancia = actual - compra
                    pct = ((ganancia) / compra) * 100
                    titulos = int(datos.get("Titulos", 0) or 0)
                    resumen = f"📊 {nombre_legible}"
                    resumen += f"\n1. Precio de compra: ${compra:.2f}"
                    resumen += f"\n2. Precio actual: ${actual:.2f}"
                    resumen += f"\n3. Ganancia: ${ganancia:.2f} ({pct:.2f}%)"
                    resumen += f"\n4. Títulos comprados: {titulos}"
                    resumen += f"\n5. Ganancia total estimada: ${ganancia * titulos:.2f}"
                    enviar_mensaje(chat_id, resumen)
                except Exception as e:
                    enviar_mensaje(chat_id, f"⚠️ Error en {nombre_legible}: {str(e)}")

    return {"ok": True}

@app.route("/")
def health():
    return "Bot funcionando correctamente ✅"

def obtener_portafolio_simulado():
    return [
        {"Nombre": "AAPL", "Costo_promedio": 100, "Precio_mercado": 120, "Titulos": 3},
        {"Nombre": "EFECTIVO", "Costo_promedio": "", "Precio_mercado": "", "Titulos": ""},
        {"Nombre": "NVDA", "Costo_promedio": 200, "Precio_mercado": 250, "Titulos": 1},
        {"Nombre": "AMZN", "Costo_promedio": 0, "Precio_mercado": 0, "Titulos": 2}
    ]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
