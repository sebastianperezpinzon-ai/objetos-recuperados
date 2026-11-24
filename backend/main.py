import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ECO-S API - Ecosistema de Conexión y Optimización Sensorial")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("Falta configurar la variable de entorno DATABASE_URL.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ==========================================
# Modelos Pydantic
# ==========================================
class LoginRequest(BaseModel):
    correo: str
    password: str


class ObjetoCreate(BaseModel):
    fecha_hallazgo: str
    lugar_hallazgo: str
    clasificacion: str
    descripcion: str
    ruta_foto: Optional[str] = None


class BajaRequest(BaseModel):
    codigo_objeto: int
    tipo_salida: str
    fecha_salida: str
    hora_salida: str
    categoria_retira: str
    nombre_retira: str
    id_funcionario: Optional[int] = None
    funcionario_turno: Optional[str] = None
    funcionario_entrega: Optional[str] = None


class ReclamoRequest(BaseModel):
    codigo_objeto: int
    nombre_solicitante: str
    correo_institucional: str
    telefono_contacto: str


class UsuarioCreate(BaseModel):
    correo: str
    contrasena: str
    rol: str


# ==========================================
# Utilidad de Notificaciones por Correo (Brevo SMTP)
# ==========================================
def enviar_correo_reclamo(reclamo: ReclamoRequest, info_objeto: dict):
    smtp_host = os.getenv("SMTP_HOST", "smtp-relay.brevo.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    sender_email = os.getenv("SENDER_EMAIL", smtp_user).strip()
    correo_logistica = os.getenv("CORREO_LOGISTICA", "").strip()

    if not smtp_user or not smtp_password:
        raise RuntimeError("Faltan las credenciales SMTP_USER o SMTP_PASSWORD de Brevo en Vercel.")

    if not sender_email:
        raise RuntimeError("Falta configurar SENDER_EMAIL (remitente verificado en Brevo).")

    # 1. Correo de confirmación para el solicitante
    msg_usuario = MIMEMultipart("alternative")
    msg_usuario["Subject"] = f"Solicitud de Reclamación - Objeto #{reclamo.codigo_objeto} (ECO-S)"
    msg_usuario["From"] = f"Objetos Recuperados EAN <{sender_email}>"
    msg_usuario["To"] = reclamo.correo_institucional

    cuerpo_html_usuario = f"""
    <div style="font-family: Arial, sans-serif; color: #212529; max-width: 600px; margin: auto; border: 1px solid #DCE1E5; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #005A43; color: #FFFFFF; padding: 1.2rem; text-align: center;">
            <h2 style="margin: 0;">Solicitud de Reclamación Registrada</h2>
        </div>
        <div style="padding: 1.5rem;">
            <p>Hola <strong>{reclamo.nombre_solicitante}</strong>,</p>
            <p>Hemos recibido tu solicitud para reclamar el siguiente elemento en custodia:</p>
            <ul>
                <li><strong>Código del Objeto:</strong> #{reclamo.codigo_objeto}</li>
                <li><strong>Categoría:</strong> {info_objeto.get('clasificacion', 'N/A')}</li>
                <li><strong>Descripción:</strong> {info_objeto.get('descripcion', 'N/A')}</li>
                <li><strong>Fecha de hallazgo:</strong> {info_objeto.get('fecha_hallazgo', 'N/A')}</li>
            </ul>
            <div style="background-color: #E8F5E9; border-left: 4px solid #005A43; padding: 1rem; margin: 1.2rem 0;">
                <strong>Instrucciones para la entrega:</strong><br>
                Acércate a la <strong>Central de Seguridad en el Sótano 1</strong> e indica el <strong>espacio físico exacto</strong> donde lo dejaste.<br><br>
                <strong>Horarios de atención:</strong><br>
                • Lunes a viernes: 9:00 a.m. a 11:00 a.m. y 5:00 p.m. a 7:00 p.m.<br>
                • Sábados: 9:00 a.m. a 12:00 m.
            </div>
            <p style="font-size: 0.85rem; color: #6C757D;">Este es un mensaje automático del sistema ECO-S.</p>
        </div>
    </div>
    """
    msg_usuario.attach(MIMEText(cuerpo_html_usuario, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg_usuario)

        # 2. Notificación interna a Logística / Seguridad (si está configurado)
        if correo_logistica:
            msg_logistica = MIMEMultipart("alternative")
            msg_logistica["Subject"] = f"[ECO-S Alerta] Nuevo reclamo para Objeto #{reclamo.codigo_objeto}"
            msg_logistica["From"] = f"Sistema ECO-S <{sender_email}>"
            msg_logistica["To"] = correo_logistica

            cuerpo_logistica = f"""
            <h3>Nueva solicitud de reclamación</h3>
            <p><strong>Objeto:</strong> #{reclamo.codigo_objeto} - {info_objeto.get('descripcion', '')} ({info_objeto.get('clasificacion', '')})</p>
            <p><strong>Lugar de hallazgo registrado:</strong> {info_objeto.get('lugar_hallazgo', 'No especificado')}</p>
            <hr>
            <p><strong>Solicitante:</strong> {reclamo.nombre_solicitante}</p>
            <p><strong>Correo institucional:</strong> {reclamo.correo_institucional}</p>
            <p><strong>Teléfono de contacto:</strong> {reclamo.telefono_contacto}</p>
            """
            msg_logistica.attach(MIMEText(cuerpo_logistica, "html", "utf-8"))
            server.send_message(msg_logistica)


# ==========================================
# Endpoints Operativos
# ==========================================
@app.get("/api/ping-db")
def ping_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM objetos;")
            total = cur.fetchone()["total"]
            return {"mensaje": "Conexión a Neon PostgreSQL exitosa", "total_objetos": total}
    finally:
        conn.close()


@app.post("/api/auth/login")
def login_usuario(credenciales: LoginRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM usuarios WHERE LOWER(correo) = LOWER(%s) LIMIT 1;",
                (credenciales.correo.strip(),)
            )
            usuario = cur.fetchone()
            clave_db = usuario.get("password_hash") if usuario else None
            if usuario and clave_db is None:
                clave_db = usuario.get("password")

            if not usuario or clave_db != credenciales.password:
                raise HTTPException(status_code=401, detail="Credenciales incorrectas o usuario no autorizado.")

            return {
                "usuario": {
                    "id_usuario": usuario.get("id_usuario"),
                    "correo": usuario.get("correo"),
                    "rol": usuario.get("rol")
                }
            }
    finally:
        conn.close()


@app.get("/api/objetos")
def listar_objetos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.*,
                       t.categoria_retira,
                       t.nombre_retira,
                       t.fecha_salida,
                       t.hora_salida,
                       t.funcionario_entrega AS funcionario_procesa
                FROM objetos o
                LEFT JOIN LATERAL (
                    SELECT * FROM trazabilidad_salidas ts
                    WHERE ts.codigo_objeto = o.codigo
                    ORDER BY ts.id_salida DESC LIMIT 1
                ) t ON true
                ORDER BY o.codigo DESC;
            """)
            return cur.fetchall()
    except psycopg2.Error:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM objetos ORDER BY codigo DESC;")
            return cur.fetchall()
    finally:
        conn.close()


@app.post("/api/objetos")
def crear_objeto(objeto: ObjetoCreate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO objetos (fecha_hallazgo, lugar_hallazgo, clasificacion, descripcion, ruta_foto, estado_actual)
                VALUES (%s, %s, %s, %s, %s, 'Activo')
                RETURNING *;
            """, (
                objeto.fecha_hallazgo,
                objeto.lugar_hallazgo,
                objeto.clasificacion,
                objeto.descripcion,
                objeto.ruta_foto
            ))
            nuevo = cur.fetchone()
            conn.commit()
            return {"mensaje": "Objeto registrado correctamente", "data": nuevo}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/api/objetos/baja")
def procesar_baja(baja: BajaRequest):
    conn = get_db_connection()
    responsable = (baja.funcionario_turno or baja.funcionario_entrega or "Sin registro").strip()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE objetos SET estado_actual = %s WHERE codigo = %s RETURNING codigo;",
                (baja.tipo_salida, baja.codigo_objeto)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Objeto #{baja.codigo_objeto} no encontrado.")

            id_func_valido = None
            if baja.id_funcionario is not None:
                cur.execute("SELECT id_usuario FROM usuarios WHERE id_usuario = %s;", (baja.id_funcionario,))
                if cur.fetchone():
                    id_func_valido = baja.id_funcionario

            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'trazabilidad_salidas';
            """)
            columnas_reales = {row["column_name"] for row in cur.fetchall()}

            datos_posibles = {
                "codigo_objeto": baja.codigo_objeto,
                "tipo_salida": baja.tipo_salida,
                "fecha_salida": baja.fecha_salida,
                "hora_salida": baja.hora_salida,
                "categoria_retira": baja.categoria_retira,
                "nombre_retira": baja.nombre_retira,
                "id_funcionario": id_func_valido,
                "id_usuario": id_func_valido,
                "funcionario_turno": responsable,
                "funcionario_entrega": responsable,
            }

            columnas_insertar = [col for col in datos_posibles if col in columnas_reales]
            if not columnas_insertar:
                raise HTTPException(status_code=500, detail="La tabla trazabilidad_salidas no tiene columnas compatibles.")

            valores = [datos_posibles[col] for col in columnas_insertar]
            placeholders = ", ".join(["%s"] * len(columnas_insertar))
            nombres_sql = ", ".join(columnas_insertar)

            cur.execute(
                f"INSERT INTO trazabilidad_salidas ({nombres_sql}) VALUES ({placeholders});",
                tuple(valores)
            )
            conn.commit()
            return {"mensaje": f"Salida del objeto #{baja.codigo_objeto} registrada exitosamente."}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error SQL en baja: {str(e)}")
    finally:
        conn.close()


@app.post("/api/objetos/solicitar-reclamo")
def solicitar_reclamo(reclamo: ReclamoRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT codigo, clasificacion, descripcion, lugar_hallazgo, fecha_hallazgo, estado_actual FROM objetos WHERE codigo = %s;",
                (reclamo.codigo_objeto,)
            )
            objeto = cur.fetchone()
            if not objeto:
                raise HTTPException(status_code=404, detail=f"El objeto #{reclamo.codigo_objeto} no existe.")
            if objeto["estado_actual"] != "Activo":
                raise HTTPException(status_code=400, detail=f"El objeto #{reclamo.codigo_objeto} ya no está disponible para reclamo.")

        enviar_correo_reclamo(reclamo, objeto)

        return {
            "mensaje": f"Solicitud registrada y correo enviado para el objeto #{reclamo.codigo_objeto}.",
            "solicitante": reclamo.nombre_solicitante
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo enviar el correo de notificación: {str(e)}")
    finally:
        conn.close()


@app.get("/api/usuarios")
def listar_usuarios():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id_usuario, correo, rol FROM usuarios ORDER BY id_usuario ASC;")
            return cur.fetchall()
    finally:
        conn.close()


@app.post("/api/usuarios")
def crear_usuario(usuario: UsuarioCreate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO usuarios (correo, password_hash, rol) VALUES (%s, %s, %s) RETURNING id_usuario, correo, rol;",
                (usuario.correo.strip().lower(), usuario.contrasena, usuario.rol)
            )
            creado = cur.fetchone()
            conn.commit()
            return {"mensaje": "Usuario creado", "usuario": creado}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
