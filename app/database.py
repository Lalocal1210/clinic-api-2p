# --- app/database.py ---

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus  # Para codificar caracteres especiales

# 1. Clase de Configuración para leer el .env
# Lee todas las variables de entorno que tu app necesita
class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    JWT_SECRET_KEY: str  # Llave secreta para los tokens

    class Config:
        env_file = ".env"  # Especifica el archivo a leer

# 2. Cargar la configuración
# Esta instancia 'settings' se importará en otros archivos (ej. security.py)
settings = Settings()

# 3. Codificar la contraseña para la URL de forma segura
# Esto maneja caracteres especiales como '#', '$', '*'
safe_password = quote_plus(settings.DB_PASSWORD)

# 4. Construir la URL de conexión
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:{safe_password}@"
    f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# 5. Motor de SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 6. Creador de Sesiones
# Esta será la clase que usaremos para crear sesiones de BBDD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 7. Clase Base para tus Modelos
# Tus clases en models.py heredarán de aquí
Base = declarative_base()