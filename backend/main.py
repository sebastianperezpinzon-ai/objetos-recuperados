import os
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
                raise HTTPException(status_code=404, detail="Objeto no encontrado.")

            cur.execute("""
                INSERT INTO trazabilidad_salidas (
                    codigo_objeto, tipo_salida, fecha_salida, hora_salida,
                    categoria_retira, nombre_retira, id_funcionario, funcionario_entrega
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                baja.codigo_objeto,
                baja.tipo_salida,
                baja.fecha_salida,
                baja.hora_salida,
                baja.categoria_retira,
                baja.nombre_retira,
                baja.id_funcionario,
                responsable
            ))
            conn.commit()
            return {"mensaje": f"Salida del objeto #{baja.codigo_objeto} registrada exitosamente."}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/objetos/solicitar-reclamo")
def solicitar_reclamo(reclamo: ReclamoRequest):
    return {
        "mensaje": f"Solicitud registrada para el objeto #{reclamo.codigo_objeto}.",
        "solicitante": reclamo.nombre_solicitante
    }

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
