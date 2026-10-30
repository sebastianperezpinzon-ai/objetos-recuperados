import sys
import os

# Obtener rutas de la raíz y del directorio backend
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")

# Registrar ambas rutas en el path de Python
sys.path.append(root_dir)
sys.path.append(backend_dir)

from backend.main import app
