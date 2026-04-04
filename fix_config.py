import json

file_path = 'config.json'
new_message = """🔥 ¡EQUÍPATE PARA RENDIR AL MÁXIMO! 🔥

💪 Enguatadas manga larga — $9 USD | 3 colores | Talla M
🏋️ Camisetas de gym — $8 USD | Talla L | Tela transpirable, ajuste atlético
🥊 Guantillas de gym — $6 USD | Máxima protección y agarre
🩳 Shorts deportivos — $8 USD | Talla M | Cómodos y ligeros
🏋️‍♂️ Faja para levantar peso — $12 USD | Talla M | Mayor soporte y seguridad
🥷 Balaclava — $4 USD | Protección y estilo
🥤 Shaker para proteínas — $9 USD | Mezcla perfecta sin grumos
🚴 Mangas deportivas (ciclismo/gym) — $1.5 USD | Protección y rendimiento
💥 Straps de gym — $7 USD | Mejora tu agarre y levanta más peso
⚡ Creatina (100 servicios, 5g c/u) — $30 USD | Potencia tu rendimiento y recuperación

🔥 Todo diseñado para alto desempeño con materiales de calidad.

📦 ¡Hacemos domicilio! Recíbelo directo en tu puerta
📩 Escríbenos por Messenger y haz tu pedido ahora
⚡ Stock limitado — ¡no te quedes sin el tuyo!"""

with open(file_path, 'r', encoding='utf-8') as f:
    data = f.read()
    if data.startswith('\ufeff'):
        data = data[1:]
    data = json.loads(data)

for account in data.get('accounts', []):
    for group in account.get('groups', []):
        group['message'] = new_message

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Precios y codificacion arreglados.")
