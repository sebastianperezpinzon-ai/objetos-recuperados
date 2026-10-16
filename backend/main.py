import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Carga de variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan las credenciales de Supabase en el archivo .env")

# 2. Cliente oficial de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. Inicialización de la aplicación FastAPI
app = FastAPI(
    title="API REST - ECO-S EAN",
    description="Sistema Nervioso Central para la gestión de objetos recuperados y trazabilidad del campus.",
    version="1.0.0"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# MODELOS DE DATOS (PYDANTIC SCHEMAS)
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
    tipo_salida: str  # 'Reclamado' o 'Baja'
    fecha_salida: str
    hora_salida: str
    categoria_retira: str
    nombre_retira: str
    id_funcionario: int  # Trazabilidad Operativa

# ==========================================
# RUTAS / ENDPOINTS
# ==========================================

@app.get("/", tags=["Sistema"])
def ruta_raiz():
    return {
        "sistema": "ECO-S EAN Backend",
        "estado": "Conectado",
        "base_datos": "Supabase PostgreSQL (Cloud)"
    }

@app.get("/api/ping-db", tags=["Sistema"])
def probar_conexion_db():
    try:
        respuesta = supabase.table("objetos").select("count", count="exact").execute()
        return {"mensaje": "Conexión a Supabase exitosa", "total_objetos": respuesta.count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar con Supabase: {str(e)}")

# ------------------------------------------
# AUTENTICACIÓN
# ------------------------------------------

@app.post("/api/auth/login", tags=["Autenticación"])
def autenticar_usuario(datos: LoginRequest):
    correo_limpio = datos.correo.strip().lower()
    
    try:
        # Consulta a la tabla 'usuarios'
        respuesta = supabase.table("usuarios") \
            .select("id_usuario, correo, rol, activo, password_hash") \
            .eq("correo", correo_limpio) \
            .execute()
        
        if not respuesta.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas o usuario inexistente"
            )
        
        usuario = respuesta.data[0]
        
        if not usuario.get("activo", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario se encuentra inactivo en la plataforma"
            )
            
        # Verificación de contraseña
        if usuario["password_hash"] != datos.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )
            
        return {
            "mensaje": "Autenticación exitosa",
            "usuario": {
                "id_usuario": usuario["id_usuario"],
                "correo": usuario["correo"],
                "rol": usuario["rol"]
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno en autenticación: {str(e)}")

# ------------------------------------------
# INVENTARIO Y OBJETOS
# ------------------------------------------

@app.get("/api/objetos", tags=["Inventario"])
def listar_objetos():
    try:
        respuesta = supabase.table("objetos").select("*").order("codigo", desc=True).execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar objetos: {str(e)}")

@app.post("/api/objetos", tags=["Inventario"])
def registrar_objeto(objeto: ObjetoCreate):
    try:
        nuevo_registro = {
            "fecha_hallazgo": objeto.fecha_hallazgo,
            "lugar_hallazgo": objeto.lugar_hallazgo,
            "clasificacion": objeto.clasificacion,
            "descripcion": objeto.descripcion,
            "ruta_foto": objeto.ruta_foto,
            "estado_actual": "Activo"
        }
        
        respuesta = supabase.table("objetos").insert(nuevo_registro).execute()
        return {"mensaje": "Objeto registrado con éxito", "data": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar objeto: {str(e)}")

@app.post("/api/objetos/baja", tags=["Trazabilidad"])
def procesar_salida_objeto(baja: BajaRequest):
    try:
        # 1. Registrar la trazabilidad de salida
        registro_salida = {
            "codigo_objeto": baja.codigo_objeto,
            "id_funcionario": baja.id_funcionario,
            "tipo_salida": baja.tipo_salida,
            "fecha_salida": baja.fecha_salida,
            "hora_salida": baja.hora_salida,
            "categoria_retira": baja.categoria_retira,
            "nombre_retira": baja.nombre_retira
        }
        supabase.table("trazabilidad_salidas").insert(registro_salida).execute()
        
        # 2. Actualizar el estado del objeto en la tabla 'objetos'
        supabase.table("objetos") \
            .update({"estado_actual": baja.tipo_salida}) \
            .eq("codigo", baja.codigo_objeto) \
            .execute()
            
        return {"mensaje": f"Objeto #{baja.codigo_objeto} actualizado exitosamente a estado '{baja.tipo_salida}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la salida: {str(e)}")