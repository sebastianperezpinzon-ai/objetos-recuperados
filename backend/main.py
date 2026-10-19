import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from supabase import create_client, Client

# Importar servicio de correo de Office 365
from email_service import enviar_correo_solicitud_reclamo

# ==========================================
# 1. CARGA DE VARIABLES DE ENTORNO Y SUPABASE
# ==========================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan las credenciales de Supabase en las variables de entorno.")

# Cliente oficial de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. INICIALIZACIÓN DE FASTAPI
# ==========================================
app = FastAPI(
    title="API REST - ECO-S EAN",
    description="Sistema Nervioso Central para la gestión de objetos recuperados, trazabilidad del campus y notificaciones institucionales.",
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
    funcionario_turno: Optional[str] = None  # Nombre del funcionario responsable en turno
    correo_notificacion: Optional[str] = None

class SolicitudReclamoPublica(BaseModel):
    codigo_objeto: int
    nombre_solicitante: str
    correo_institucional: str
    telefono_contacto: Optional[str] = None

class UsuarioCreate(BaseModel):
    correo: str
    contrasena: str
    rol: str

# ==========================================
# RUTAS DE SISTEMA Y SALUD
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

# ==========================================
# MÓDULO: AUTENTICACIÓN
# ==========================================

@app.post("/api/auth/login", tags=["Autenticación"])
def autenticar_usuario(datos: LoginRequest):
    correo_limpio = datos.correo.strip().lower()
    
    try:
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

# ==========================================
# MÓDULO: SOLICITUD PÚBLICA (INDEX)
# ==========================================

@app.post("/api/objetos/solicitar-reclamo", tags=["Público"])
def solicitar_reclamo_publico(solicitud: SolicitudReclamoPublica, background_tasks: BackgroundTasks):
    try:
        # 1. Verificar existencia y estado activo del objeto
        res = supabase.table("objetos").select("*").eq("codigo", solicitud.codigo_objeto).execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="El objeto especificado no existe en el catálogo.")
        
        objeto = res.data[0]
        if objeto.get("estado_actual") != "Activo":
            raise HTTPException(status_code=400, detail="Este objeto ya fue procesado o entregado previamente.")

        # 2. Empaquetar datos para la notificación por correo
        datos_correo = {
            "codigo_objeto": solicitud.codigo_objeto,
            "nombre_retira": solicitud.nombre_solicitante
        }

        # 3. Disparar correo asíncrono vía Office 365
        background_tasks.add_task(
            enviar_correo_solicitud_reclamo,
            destinatario_solicitante=solicitud.correo_institucional,
            datos_baja=datos_correo
        )

        return {
            "status": "success",
            "mensaje": f"Solicitud para el objeto #{solicitud.codigo_objeto} registrada. Se han enviado las notificaciones por correo."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la solicitud pública: {str(e)}")

# ==========================================
# MÓDULO: INVENTARIO Y OBJETOS
# ==========================================

@app.get("/api/objetos", tags=["Inventario"])
def listar_objetos():
    try:
        # 1. Consultar todos los objetos
        respuesta_obj = supabase.table("objetos").select("*").order("codigo", desc=True).execute()
        objetos = respuesta_obj.data

        # 2. Consultar la tabla de trazabilidad de salidas
        salidas_dict = {}
        try:
            respuesta_salidas = supabase.table("trazabilidad_salidas").select("*").execute()
            for salida in respuesta_salidas.data:
                salidas_dict[salida["codigo_objeto"]] = salida
        except Exception as e_salidas:
            print("Aviso al consultar trazabilidad_salidas:", str(e_salidas))

        # 3. Enriquecer cada objeto con la información de su salida (si aplica)
        for obj in objetos:
            salida = salidas_dict.get(obj["codigo"])
            if salida:
                obj["nombre_retira"] = salida.get("nombre_retira")
                obj["categoria_retira"] = salida.get("categoria_retira")
                obj["funcionario_procesa"] = salida.get("funcionario_turno") or salida.get("nombre_funcionario")
                obj["fecha_salida"] = salida.get("fecha_salida")
                obj["hora_salida"] = salida.get("hora_salida")
            else:
                obj["nombre_retira"] = None
                obj["categoria_retira"] = None
                obj["funcionario_procesa"] = None
                obj["fecha_salida"] = None
                obj["hora_salida"] = None

        return objetos
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
def procesar_salida_objeto(baja: BajaRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Registrar la trazabilidad de salida incluyendo el funcionario en turno
        registro_salida = {
            "codigo_objeto": baja.codigo_objeto,
            "id_funcionario": baja.id_funcionario,
            "tipo_salida": baja.tipo_salida,
            "fecha_salida": baja.fecha_salida,
            "hora_salida": baja.hora_salida,
            "categoria_retira": baja.categoria_retira,
            "nombre_retira": baja.nombre_retira,
            "funcionario_turno": baja.funcionario_turno
        }
        
        try:
            supabase.table("trazabilidad_salidas").insert(registro_salida).execute()
        except Exception as insert_err:
            # Fallback en caso de variación de nombre de columna en la BD
            if "funcionario_turno" in str(insert_err):
                del registro_salida["funcionario_turno"]
                registro_salida["nombre_funcionario"] = baja.funcionario_turno
                supabase.table("trazabilidad_salidas").insert(registro_salida).execute()
            else:
                raise insert_err

        # 2. Actualizar el estado del objeto en la tabla 'objetos'
        supabase.table("objetos") \
            .update({"estado_actual": baja.tipo_salida}) \
            .eq("codigo", baja.codigo_objeto) \
            .execute()

        # 3. Tarea en segundo plano para notificación por correo
        if baja.correo_notificacion:
            background_tasks.add_task(
                enviar_correo_solicitud_reclamo,
                destinatario_solicitante=baja.correo_notificacion,
                datos_baja=baja.dict()
            )

        return {"mensaje": f"Objeto #{baja.codigo_objeto} actualizado exitosamente a estado '{baja.tipo_salida}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la salida: {str(e)}")
# ==========================================
# MÓDULO: GESTIÓN DE USUARIOS (ADMINISTRACIÓN)
# ==========================================

@app.get("/api/usuarios", tags=["Usuarios"])
def obtener_usuarios():
    try:
        respuesta = supabase.table("usuarios").select("id_usuario, correo, rol, activo").execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar usuarios: {str(e)}")

@app.post("/api/usuarios", tags=["Usuarios"])
def crear_usuario(usuario: UsuarioCreate):
    correo_limpio = usuario.correo.strip().lower()
    try:
        # Verificar si el correo ya existe
        existente = supabase.table("usuarios").select("id_usuario").eq("correo", correo_limpio).execute()
        if existente.data:
            raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado en el sistema.")

        nuevo_usuario = {
            "correo": correo_limpio,
            "password_hash": usuario.contrasena,
            "rol": usuario.rol,
            "activo": True
        }
        
        respuesta = supabase.table("usuarios").insert(nuevo_usuario).execute()
        return {"mensaje": "Usuario registrado exitosamente", "data": respuesta.data[0]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")
