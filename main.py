import requests
from flask import Flask, request

app = Flask(__name__)

# 🔐 Reemplaza esto con tu token si llega a cambiar
TOKEN = '8134078439:AAFD5vneih7t7356EJ440xNzjibYJb3Dlu0'
URL = f'https://api.telegram.org/bot{TOKEN}/'

def enviar_mensaje(chat_id, texto):
    requests.post(URL + 'sendMessage', json={
        'chat_id': chat_id,
        'text': texto
    })

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    datos = request.get_json()
    if 'message' in datos:
        chat_id = datos['message']['chat']['id']
        texto = datos['message'].get('text', '')

        if texto == '/start':
            enviar_mensaje(chat_id, "👋 ¡Bienvenido Miguel! Usa /resumen para ver tu portafolio.")
        elif texto == '/resumen':
            enviar_mensaje(chat_id, "📊 Aquí va tu resumen de hoy (contenido real muy pronto).")
        else:
            enviar_mensaje(chat_id, "🤖 Comando no reconocido. Usa /resumen o /start.")
    return {'ok': True}

@app.route('/')
def inicio():
    return 'Bot corriendo correctamente ✔️'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
