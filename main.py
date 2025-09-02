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
    
    prompt = f"""Extrae información de este mensaje de tarjeta:

{message_text}

Si contiene "Status" con "Approved", responde:
{{
  "valid": true,
  "card": "tarjeta encontrada",
  "status": "Approved",
  "response": "respuesta encontrada",
  "bank": "banco encontrado",
  "type": "tipo encontrado",
  "country": "país encontrado",
  "gateway": "gateway encontrado"
}}

Si NO tiene "Status" con "Approved": {{"valid": false}}"""
    
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

def clean_markdown(text):
    # Limpiar formato Markdown de mensajes de bots
    import re
    # Remover enlaces [texto](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remover ** bold **
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    # Remover * italic *
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    # Remover ` code `
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text

def contains_card_info(text):
    # Filtros para detectar mensajes de tarjetas
    card_indicators = [
        'card', 'cc', 'status', 'approved', 'declined', 'response', 'gateway',
        'cvv', 'exp', 'bank', 'issuer', 'visa', 'mastercard', 'amex',
        '|', 'mm/yy', 'mm/yyyy', '⇾', '-»', '〄', '┊', 'chk', 'auth',
        'payflow', 'avs', 'detalles', 'información', 'perfil', '↳', '么', '⌁',
        'nagisa', 'stripe', 'bin', 'details', 'segs', 'checked by', '⤷', 'あ',
        'yumeko', 'vbv', 'braintree', 'retries', 'authenticate'
    ]
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in card_indicators)



client = TelegramClient(
    'ryuko_scrapper_session', 
    api_id, 
    api_hash,
    auto_reconnect=True,
    connection_retries=None,
    retry_delay=1
)

@client.on(events.MessageEdited)
async def handler(event):
    try:
        if event.text and contains_card_info(event.text):
            # Verificar que el mensaje esté completo (contenga Status y resultado)
            text_lower = event.text.lower()
            if not ('status' in text_lower and ('approved' in text_lower or 'declined' in text_lower)):
                return  # Mensaje incompleto, esperar más ediciones
                
            print(f"[DEBUG] Mensaje completo: {event.text[:100]}...")
            # Limpiar formato Markdown antes de enviar a Gemini
            clean_text = clean_markdown(event.text)
            print(f"[DEBUG] Texto limpio enviado a Gemini: {clean_text}")
            
            # Validación simple antes de Gemini
            if 'approved' in clean_text.lower() and 'status' in clean_text.lower():
                # Extraer información directamente del texto
                lines = clean_text.split('\n')
                card = "N/A"
                status = "Approved"
                response = "N/A"
                bank = "N/A"
                gateway = "N/A"
                country = "N/A"
                
                for line in lines:
                    line_lower = line.lower()
                    if ('cc' in line_lower or 'card' in line_lower) and '|' in line:
                        # Extraer tarjeta completa
                        parts = line.split('|')
                        if len(parts) >= 4:
                            card_num = parts[0].split()[-1]
                            card = f"{card_num}|{parts[1]}|{parts[2]}|{parts[3]}"
                    elif 'response' in line_lower and ':' in line:
                        response = line.split(':')[-1].strip()
                    elif 'bank' in line_lower and ':' in line:
                        bank = line.split(':')[-1].strip()
                    elif ('gate' in line_lower or 'gateway' in line_lower) and ':' in line:
                        gateway = line.split(':')[-1].strip()
                    elif 'country' in line_lower and ':' in line:
                        country = line.split(':')[-1].strip()
                    # También manejar otros separadores
                    elif 'response' in line_lower:
                        if '↳' in line: response = line.split('↳')[-1].strip()
                        elif '┊' in line: response = line.split('┊')[-1].strip()
                        elif '⇾' in line: response = line.split('⇾')[-1].strip()
                        elif '⤷' in line: response = line.split('⤷')[-1].strip()
                    elif 'bank' in line_lower:
                        if '↳' in line: bank = line.split('↳')[-1].strip()
                        elif '┊' in line: bank = line.split('┊')[-1].strip()
                        elif '⇾' in line: bank = line.split('⇾')[-1].strip()
                        elif '⤷' in line: bank = line.split('⤷')[-1].strip()
                    elif ('gateway' in line_lower or 'retries' in line_lower or 'gate' in line_lower):
                        if '↳' in line: gateway = line.split('↳')[-1].strip()
                        elif '┊' in line: gateway = line.split('┊')[-1].strip()
                        elif '⇾' in line: gateway = line.split('⇾')[-1].strip()
                        elif '⤷' in line: gateway = line.split('⤷')[-1].strip()
                    elif 'country' in line_lower:
                        if '↳' in line: country = line.split('↳')[-1].strip()
                        elif '┊' in line: country = line.split('┊')[-1].strip()
                        elif '⇾' in line: country = line.split('⇾')[-1].strip()
                        elif '⤷' in line: country = line.split('⤷')[-1].strip()
                
                print(f"[DIRECT] Tarjeta válida encontrada: {card}")
                valid = True
            else:
                gemini_result = analyze_with_gemini(clean_text)
                valid = gemini_result.get("valid")
                if valid:
                    card = gemini_result.get("card", "N/A")
                    status = gemini_result.get("status", "N/A")
                    response = gemini_result.get("response", "N/A")
                    bank = gemini_result.get("bank", "N/A")
                    gateway = gemini_result.get("gateway", "N/A")
                    country = gemini_result.get("country", "N/A")
            
            if valid:
                typ = "N/A"
                
                plantilla = (
                    "| 𝗥𝗬𝗨𝗞𝗢 𝙎𝘾𝙍𝘼𝙋𝙋𝙀𝙍 |\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"[❀] 𝘾𝘾 -» {card}\n"
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
    except Exception as e:
        print(f"[ERROR] Handler falló: {e}")

async def main():
    while True:
        try:
            print('𝗥𝗬𝗨𝗞𝗢 𝙎𝘾𝙍𝘼𝙋𝙋𝙀𝙍 iniciando...')
            await client.start()
            print("Cliente conectado!")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"[ERROR] Cliente desconectado: {e}")
            await asyncio.sleep(5)
            print("Reintentando conexión...")

if __name__ == '__main__':
    asyncio.run(main())
