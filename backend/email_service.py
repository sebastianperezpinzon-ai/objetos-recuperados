import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ECO-S - Universidad EAN")

# Correos institucionales fijos para notificación y seguimiento de seguridad/logística
CORREOS_INSTITUCIONALES = [
    "logisyaudio@universidadean.edu.co",
    "colviseg@universidadean.edu.co"
]

def enviar_correo_solicitud_reclamo(destinatario_solicitante: str, datos_baja: dict):
    """
    Envía la notificación automática de reclamación a:
    1. El correo ingresado por el solicitante (estudiante o funcionario).
    2. logisyaudio@universidadean.edu.co
    3. colviseg@universidadean.edu.co
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[ECO-S EMAIL O365] Servidor SMTP Office 365 no configurado. Se omite el envío.")
        return

    # Consolidar lista de destinatarios sin duplicados
    todos_los_destinatarios = list(set([destinatario_solicitante] + CORREOS_INSTITUCIONALES))

    asunto = f"Solicitud de Reclamación - Objeto #{datos_baja['codigo_objeto']}"
    
    # Texto en plano exacto según requerimiento
    cuerpo_texto = f"""Cordial saludo.
Se ha generado la solicitud por el elemento "#{datos_baja['codigo_objeto']}" por parte de "{datos_baja['nombre_retira']}".
Recuerda tener el dato del espacio físico o lugar donde lo dejaste y acercarte a la central de seguridad en el sótano 1 de lunes a viernes en los espacios de 9am a 11am y 5pm a 7pm. 
Si tienes alguna duda puedes escribir un correo a logisyaudio@universidadean.edu.co.
Muchas gracias."""

    # Plantilla HTML respetando la redacción exacta e identidad institucional
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
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
            <p>Se ha generado la solicitud por el elemento "<strong>#{datos_baja['codigo_objeto']}</strong>" por parte de "<strong>{datos_baja['nombre_retira']}</strong>".</p>
            <p>Recuerda tener el dato del espacio físico o lugar donde lo dejaste y acercarte a la central de seguridad en el sótano 1 de lunes a viernes en los espacios de 9am a 11am y 5pm a 7pm, los sábados de 9am a 12m.</p>
            <p>Si tienes alguna duda puedes escribir un correo a <a href="mailto:logisyaudio@universidadean.edu.co">logisyaudio@universidadean.edu.co</a>.</p>
            <p>Muchas gracias.</p>
            <div class="footer">
                <p><strong>Ecosistema ECO-S EAN</strong> — Gestión Sostenible de Planta Física y Bienestar Campus (ODS 3, 4, 11 y 12)</p>
            </div>
        </div>
    </body>
    </html>
    """

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = f"{EMAIL_FROM_NAME} <{SMTP_USER}>"
    mensaje["To"] = destinatario_solicitante
    mensaje["Cc"] = ", ".join(CORREOS_INSTITUCIONALES)
    
    mensaje.attach(MIMEText(cuerpo_texto, "plain"))
    mensaje.attach(MIMEText(cuerpo_html, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        # Se envía a la lista completa de direcciones (To + Cc)
        server.sendmail(SMTP_USER, todos_los_destinatarios, mensaje.as_string())
        server.quit()
        print(f"[ECO-S EMAIL O365] Notificación enviada a: {', '.join(todos_los_destinatarios)}")
    except Exception as e:
        print(f"[ECO-S EMAIL ERROR O365] Falló el envío del mensaje: {e}")