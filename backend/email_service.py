import os
import smtplib
import socket
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from dotenv import load_dotenv

load_dotenv()

# Configuración del servidor SMTP de Office 365
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ECO-S - Universidad EAN")

CORREOS_INSTITUCIONALES = [
    "logisyaudio@universidadean.edu.co",
    "colviseg@universidadean.edu.co"
]

def enviar_correo_solicitud_reclamo(destinatario_solicitante: str, datos_baja: dict):
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[ECO-S EMAIL O365] ERROR: Credenciales SMTP no configuradas.", flush=True)
        return

    destinatario_limpio = destinatario_solicitante.strip().lower() if destinatario_solicitante else ""
    if not destinatario_limpio:
        print("[ECO-S EMAIL O365] ERROR: Correo destinatario inválido.", flush=True)
        return

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

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = Header(asunto, "utf-8")
    mensaje["From"] = f"{EMAIL_FROM_NAME} <{SMTP_USER}>"
    mensaje["To"] = destinatario_limpio
    mensaje["Cc"] = ", ".join(CORREOS_INSTITUCIONALES)

    mensaje.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    # PARCHE: Forzar resolución IPv4 para evitar "Network is unreachable" en Render
    original_getaddrinfo = socket.getaddrinfo

    def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
        return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = getaddrinfo_ipv4

    try:
        print(f"[ECO-S EMAIL O365] Conectando por IPv4 al servidor SMTP {SMTP_SERVER}:{SMTP_PORT}...", flush=True)
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, todos_los_destinatarios, mensaje.as_string())
        server.quit()
        print(f"[ECO-S EMAIL O365] Notificación enviada exitosamente a: {', '.join(todos_los_destinatarios)}", flush=True)
    except Exception as e:
        print(f"[ECO-S EMAIL ERROR O365] Falló el envío del mensaje: {str(e)}", flush=True)
        print(f"[ECO-S EMAIL ERROR O365] Detalle técnico:\n{traceback.format_exc()}", flush=True)
    finally:
        # Restaurar la resolución original del sistema
        socket.getaddrinfo = original_getaddrinfo
