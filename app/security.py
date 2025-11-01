# --- app/security.py ---

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

# Importamos la configuración (que ya leyó el .env)
from .database import settings

# --- 1. Configuración de Hashing de Contraseñas ---

# Usamos bcrypt como el algoritmo de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara una contraseña en texto plano con un hash almacenado.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Genera un hash bcrypt a partir de una contraseña en texto plano.
    """
    return pwd_context.hash(password)


# --- 2. Configuración de Autenticación JWT (Tokens) ---

# Leemos las variables desde el objeto 'settings' importado
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
# Puedes hacer esto una variable de entorno si quieres
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # El token durará 1 hora

def create_access_token(data: dict) -> str:
    """
    Crea un nuevo token JWT a partir de un diccionario de datos.
    
    'data' debe contener la información a codificar, 
    comúnmente el 'sub' (subject) con el email o id del usuario.
    """
    to_encode = data.copy()
    
    # Establece el tiempo de expiración
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Codifica el token usando la llave secreta y el algoritmo
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    """
    Decodifica un token JWT.
    
    Devuelve el payload (los datos internos) si el token es válido
    y no ha expirado. Devuelve None si hay un error.
    """
    try:
        # Intenta decodificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # El token es inválido, ha expirado, o la firma no coincide
        return None