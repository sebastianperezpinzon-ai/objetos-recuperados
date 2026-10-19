import os
import traceback
import resend
from dotenv import load_dotenv

load_dotenv()

# Carga de la API Key de Resend y Remitente
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "ECO-S EAN <onboarding@resend.dev>").strip()

# Correos institucionales para seguimiento de seguridad y logística
CORREOS_INSTITUCIONALES = [
    "logisyaudio@universidadean.edu.co",
    "colviseg@universidadean.edu.co"
]

def enviar_correo_solicitud_reclamo(destinatario_solicitante: str, datos_baja: dict):
    if not RESEND_API_KEY:
        print("[ECO-S RESEND ERROR] Falta la variable RESEND_API_KEY en el entorno de Render.", flush=True)
        return

    destinatario_limpio = destinatario_solicitante.strip().lower() if destinatario_solicitante else ""
    if not destinatario_limpio:
        print("[ECO-S RESEND ERROR] Dirección de correo solicitante no válida.", flush=True)
        return

    # Si estamos en modo de prueba con el remitente por defecto de Resend,
    # solo se permite enviar al correo del propietario (sebastian.perezpinzon@gmail.com)
    if "onboarding@resend.dev" in EMAIL_FROM:
        todos_los_destinatarios = ["sebastian.perezpinzon@gmail.com"]
        print("[ECO-S RESEND] MODO PRUEBA: Redirigiendo envío a la cuenta del propietario (sebastian.perezpinzon@gmail.com).", flush=True)
    else:
        todos_los_destinatarios = list(set([destinatario_limpio] + [c.strip().lower() for c in CORREOS_INSTITUCIONALES]))

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

    resend.api_key = RESEND_API_KEY

    try:
        print(f"[ECO-S RESEND] Enviando correo vía API HTTPS a {len(todos_los_destinatarios)} destinatario(s)...", flush=True)
        
        respuesta = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": todos_los_destinatarios,
            "subject": asunto,
            "text": cuerpo_texto,
            "html": cuerpo_html
        })
        
        id_mensaje = respuesta.get("id") if isinstance(respuesta, dict) else getattr(respuesta, "id", "OK")
        print(f"[ECO-S RESEND SUCCESS] Notificación enviada exitosamente. Message ID: {id_mensaje}", flush=True)
    except Exception as e:
        print(f"[ECO-S RESEND ERROR] Falló el envío del mensaje vía API HTTPS: {str(e)}", flush=True)
        print(f"[ECO-S RESEND ERROR] Detalle técnico:\n{traceback.format_exc()}", flush=True)
