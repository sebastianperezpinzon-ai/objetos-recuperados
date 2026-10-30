import sys
import os

# Agrega la raíz del repositorio al path para poder importar desde la carpeta backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
