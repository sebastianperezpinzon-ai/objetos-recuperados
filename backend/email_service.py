import os
import requests
import traceback
from dotenv import load_dotenv

load_dotenv()

# Declaración de variables globales de Brevo (AQUÍ ESTABA EL FALTANTE)
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ECO-S - Universidad EAN").strip()

CORREOS_INSTITUCIONALES = [
    "logisyaudio@universidadean.edu.co",
    "colviseg@universidadean.edu.co"
]

def enviar_correo_solicitud_reclamo(destinatario_solicitante: str, datos_baja: dict):
    """
    Envía la notificación de reclamación utilizando la API REST v3 de Brevo sobre HTTPS (Puerto 443).
    """
    # Validar que existan las credenciales necesarias
    if not BREVO_API_KEY or not EMAIL_FROM_ADDRESS:
        print("[ECO-S BREVO ERROR] Configuración incompleta: Asegúrate de definir BREVO_API_KEY y EMAIL_FROM_ADDRESS en Render.", flush=True)
        return

    destinatario_limpio = destinatario_solicitante.strip().lower() if destinatario_solicitante else ""
    if not destinatario_limpio:
        print("[ECO-S BREVO ERROR] Correo destinatario no válido.", flush=True)
        return

    codigo_obj = datos_baja.get("codigo_objeto", "N/A")
    nombre_retira = datos_baja.get("nombre_retira", "Solicitante")

    asunto = f"Solicitud de Reclamación - Objeto #{codigo_obj}"

    cuerpo_texto = f"""Cordial saludo.

Se ha generado la solicitud por el elemento "#{codigo_obj}" por parte de "{nombre_retira}".

Recuerda tener el dato del espacio físico o lugar donde lo dejaste y acercarte a la central de seguridad en el sótano 1 de lunes a viernes en los espacios de 9am a 11am y 5pm a 7pm, los sábados de 9am a 12m.

Si tienes alguna duda puedes escribir un correo a logisyaudio@universidadean.edu.co.

Muchas gracias."""

    cuerpo_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; color: #2c3e50; }}
        .container {{ max-width: 600px; background-color: #ffffff; margin: 0 auto; padding: 30px; border-radius: 8px; border-top: 5px solid #005A43; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        p {{ line-height: 1.6; font-size: 1rem; margin-bottom: 15px; }}
        .footer {{ font-size: 0.82rem; color: #6c757d; border-top: 1px solid #eee; padding-top: 15px; margin-top: 25px; }}
    </style>
</head>
<body>
    <div class="container">
        <p>Cordial saludo.</p>
        <p>Se ha generado la solicitud por el elemento "<strong>#{codigo_obj}</strong>" por parte de "<strong>{nombre_retira}</strong>".</p>
        <p>Recuerda tener el dato del espacio físico o lugar donde lo dejaste y acercarte a la central de seguridad en el sótano 1 de lunes a viernes en los espacios de 9am a 11am y 5pm a 7pm, los sábados de 9am a 12m.</p>
        <p>Si tienes alguna duda puedes escribir un correo a <a href="mailto:logisyaudio@universidadean.edu.co">logisyaudio@universidadean.edu.co</a>.</p>
        <p>Muchas gracias.</p>
        <div class="footer">
            <p><strong>Ecosistema ECO-S EAN</strong> — Gestión Sostenible de Planta Física y Bienestar Campus (ODS 3, 4, 11 y 12)</p>
        </div>
    </div>
</body>
</html>"""

    # Construcción de la carga útil para la API v3 de Brevo
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    payload = {
        "sender": {
            "name": EMAIL_FROM_NAME,
            "email": EMAIL_FROM_ADDRESS
        },
        "to": [
            {"email": destinatario_limpio}
        ],
        "cc": [
            {"email": c.strip().lower()} for c in CORREOS_INSTITUCIONALES
        ],
        "subject": asunto,
        "textContent": cuerpo_texto,
        "htmlContent": cuerpo_html
    }

    try:
        print(f"[ECO-S BREVO] Enviando notificación HTTP POST a Brevo para {destinatario_limpio}...", flush=True)
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code in [200, 201]:
            res_json = response.json()
            message_id = res_json.get("messageId", "OK")
            print(f"[ECO-S BREVO SUCCESS] Correo entregado a la API. Message ID: {message_id}", flush=True)
        else:
            print(f"[ECO-S BREVO ERROR] Brevo respondió con código {response.status_code}: {response.text}", flush=True)

    except Exception as e:
        print(f"[ECO-S BREVO ERROR] Excepción al conectar con la API de Brevo: {str(e)}", flush=True)
        print(f"[ECO-S BREVO ERROR] Detalle técnico:\n{traceback.format_exc()}", flush=True)
