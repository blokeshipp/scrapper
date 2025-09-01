from telethon import TelegramClient, events
import re
import asyncio
import requests
import json
from datetime import datetime

api_id = 23543117
api_hash = '2f73f31c59cd4e228c687daf0c95e856'
phone = '+18297783116'
destination_chat = -1002714535417

PATTERN = re.compile(
    r'𝗖𝗮𝗿𝗱\s*⇾\s*([^\n]+).*?𝗦𝘁𝗮𝘁𝘂𝘀\s*⇾\s*([^\n]+)'
    r'.*?𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲\s*⇾\s*([^\n]+)'
    r'.*?𝗜𝘀𝘀𝘂𝗲𝗿\s*⇾\s*([^\n]+)'
    r'.*?𝗜𝗻𝗳𝗼\s*⇾\s*([^\n]+)'
    r'.*?𝗖𝗼𝘂𝗻𝘁𝗿𝘆\s*⇾\s*([^\n]+)'
    r'.*?𝗚𝗮𝘁𝗲𝘄𝗮𝘆\s*⇾\s*([^\n]+)', re.DOTALL | re.IGNORECASE
)

BAD_RESPONSES = [
    'declined', 'error', 'failed', 'denied',
    'rejected', 'unsuccessful', 'invalid',
    'your card was declined', '2044: declined - call issuer'
]

GEMINI_API_KEY = "AIzaSyDu6m9S0Lv09X7JIlnwxJLqrLMd1EUDNyk"

def analyze_with_gemini(message_text):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    prompt = f"""Analiza este mensaje de tarjeta de crédito y extrae la información.

Mensaje: {message_text}

REGLA PRINCIPAL: Solo importa el campo STATUS. Ignora completamente el Result/Response.

Si el STATUS dice "Approved" (con o sin emojis), la tarjeta es válida.
Si el STATUS dice "Declined", "Failed", "Error", la tarjeta NO es válida.

Si el STATUS es "Approved":
{{
  "valid": true,
  "card": "número completo: 1234567890123456|MM|YYYY|CVV",
  "status": "status encontrado",
  "response": "resultado/respuesta encontrada",
  "bank": "banco",
  "type": "tipo",
  "country": "país",
  "gateway": "gateway"
}}

Si el STATUS NO es "Approved": {{"valid": false}}"""
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            # Extraer JSON del texto
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
    except:
        pass
    return {"valid": False}

def contains_card_info(text):
    # Filtros para detectar mensajes de tarjetas
    card_indicators = [
        'card', 'cc', 'status', 'approved', 'declined', 'response', 'gateway',
        'cvv', 'exp', 'bank', 'issuer', 'visa', 'mastercard', 'amex',
        '|', 'mm/yy', 'mm/yyyy', '⇾', '-»'
    ]
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in card_indicators)



client = TelegramClient('ryuko_scrapper_session', api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    if event.text and contains_card_info(event.text):
        print(f"[DEBUG] Nuevo mensaje: {event.text[:100]}...")
        gemini_result = analyze_with_gemini(event.text)
        if gemini_result.get("valid"):
            cc = gemini_result.get("card", "N/A")
            status = gemini_result.get("status", "N/A")
            response = gemini_result.get("response", "N/A")
            bank = gemini_result.get("bank", "N/A")
            typ = gemini_result.get("type", "N/A")
            country = gemini_result.get("country", "N/A")
            gateway = gemini_result.get("gateway", "N/A")
            
            print(f"[GEMINI] Tarjeta válida encontrada: {cc}")
            
            plantilla = (
                "| 𝗥𝗬𝗨𝗞𝗢 𝙎𝘾𝙍𝘼𝙋𝙋𝙀𝙍 |\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"[❀] 𝘾𝘾 -» {cc}\n"
                f"[❀] 𝙎𝙩𝙖𝙩𝙪𝙨 -» {status}\n"
                f"[❀] 𝙍𝙚𝙨𝙥𝙤𝙣𝙨𝙚 -» {response}\n"
                f"[❀] 𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» {gateway}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"[❀] 𝙏𝙮𝙥𝙚 -» {typ}\n"
                f"[❀] 𝘽𝙖𝙣𝙠 -» {bank}\n"
                f"[❀] 𝘾𝙤𝙪𝙣𝙩𝙧𝙮 -» {country}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            try:
                await client.send_message(destination_chat, plantilla, file='foto.png')
            except:
                await client.send_message(destination_chat, plantilla)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Mensaje scrapeado con Gemini y enviado!")
        else:
            print(f"[GEMINI] Mensaje no válido o no aprobado")

def main():
    print('𝗥𝗬𝗨𝗞𝗢 𝙎𝘾𝙍𝘼𝙋𝙋𝙀𝙍 monitoreando TODOS los chats en tiempo real...')
    with client:
        client.run_until_disconnected()

if __name__ == '__main__':
    main()
