import sys
import os

# Permite que Vercel encuentre la carpeta 'backend' en el path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
