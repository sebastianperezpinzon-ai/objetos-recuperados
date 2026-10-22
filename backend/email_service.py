import os
import requests
import traceback
from dotenv import load_dotenv

load_dotenv()

# Variables globales
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ECO-S - Universidad EAN").strip()

CORREOS_INSTITUCIONALES = [
    "logisyaudio@universidadean.edu.co",
    "colviseg@universidadean.edu.co"
]

def enviar_correo_solicitud_reclamo(destinatario_solicitante: str, datos_baja: dict):
    """
    Envía la notificación de reclamación vía Brevo API v3.
    """
    if not BREVO_API_KEY or not EMAIL_FROM_ADDRESS:
        print("[ECO-S BREVO ERROR] Configuración incompleta: Define BREVO_API_KEY y EMAIL_FROM_ADDRESS en Render.", flush=True)
        return

    destinatario_limpio = destinatario_solicitante.strip().lower() if destinatario_solicitante else ""
    if not destinatario_limpio:
        print("[ECO-S BREVO ERROR] Correo destinatario no válido.", flush=True)
        return

    codigo_obj = datos_baja.get("codigo_objeto", "N/A")
    nombre_retira = datos_baja.get("nombre_retira", "Solicitante")

    asunto = f"Confirmación de Solicitud de Objeto {codigo_obj} - Universidad EAN"

    cuerpo_texto = f"""Cordial saludo, {nombre_retira}.

Hemos recibido tu solicitud de reclamación para el objeto identificado con el código {codigo_obj} en la plataforma ECO-S.

Pasos para la entrega:
1. Ten presente el lugar exacto donde dejaste el elemento.
2. Acércate a la Central de Seguridad ubicada en el Sótano 1 de la universidad.
3. Horarios de atención:
   - Lunes a viernes: 9:00 a.m. a 11:00 a.m. y 5:00 p.m. a 7:00 p.m.
   - Sábados: 9:00 a.m. a 12:00 m.

Si tienes inquietudes, puedes responder a este correo o escribir a logisyaudio@universidadean.edu.co.

Atentamente,
Gestión de Planta Física y Logística — Universidad EAN"""

    cuerpo_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; color: #2c3e50;">
    <div style="display: none; max-height: 0px; overflow: hidden;">
        Confirmación de solicitud para el objeto {codigo_obj} en la Central de Seguridad.
    </div>

    <div style="max-width: 600px; background-color: #ffffff; margin: 0 auto; padding: 30px; border-radius: 8px; border-top: 5px solid #005A43; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
        <h2 style="color: #005A43; margin-top: 0; font-size: 1.3rem;">Solicitud de Reclamación Registrada</h2>
        <p>Cordial saludo, <strong>{nombre_retira}</strong>.</p>
        <p>Se ha generado la solicitud para el elemento identificado con el código <strong>{codigo_obj}</strong> en el sistema ECO-S.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #F2A900; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0 0 10px 0; font-weight: bold; color: #005A43;">Pasos para retirar tu objeto:</p>
            <ul style="margin: 0; padding-left: 20px; font-size: 0.95rem;">
                <li>Ten presente el espacio físico o aula donde dejaste el elemento.</li>
                <li>Preséntate en la <strong>Central de Seguridad (Sótano 1)</strong> con tu documento de identidad.</li>
                <li><strong>Horarios:</strong> Lunes a viernes (9:00 a.m. - 11:00 a.m. / 5:00 p.m. - 7:00 p.m.) y Sábados (9:00 a.m. - 12:00 m.).</li>
            </ul>
        </div>

        <p style="font-size: 0.9rem;">Si tienes alguna duda, puedes escribir a <a href="mailto:logisyaudio@universidadean.edu.co" style="color: #005A43; font-weight: bold;">logisyaudio@universidadean.edu.co</a>.</p>
        
        <div style="font-size: 0.8rem; color: #6c757d; border-top: 1px solid #eee; padding-top: 15px; margin-top: 25px;">
            <p style="margin: 0;"><strong>Ecosistema ECO-S EAN</strong> — Infraestructura, Planta Física y Bienestar Campus (ODS 3, 4, 11 y 12)</p>
        </div>
    </div>
</body>
</html>"""

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
        "replyTo": {
            "name": "Logística y Audiovisuales EAN",
            "email": "logisyaudio@universidadean.edu.co"
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
        print(f"[ECO-S BREVO] Enviando notificación a Brevo para {destinatario_limpio}...", flush=True)
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
