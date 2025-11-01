# --- app/routers/users.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Importamos todo lo necesario (con importaciones relativas)
from .. import models, schemas, security
from ..database import SessionLocal

# 1. Creamos el "esquema" de seguridad
# Esto le dice a FastAPI "busca un 'Authorization: Bearer <token>' en el header"
# El 'tokenUrl="auth/login"' le dice a los /docs a qué endpoint ir para obtener el token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 2. Creamos el router
router = APIRouter(
    prefix="/users",  # Todos los endpoints aquí empezarán con /users
    tags=["Users"]    # Los agrupa como "Users" en los /docs
)

# 3. Dependencia para la BBDD (la copiamos de auth.py)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Dependencia de Seguridad (¡El Guardia Principal!)
# Esta es la función que "protege" nuestros endpoints
def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> models.User:
    """
    Decodifica el token, encuentra al usuario en la BBDD y lo devuelve.
    Si algo falla (token inválido, usuario no existe), lanza un error 401.
    """
    
    # Intenta decodificar el token
    payload = security.decode_access_token(token)
    if payload is None:
        # Si el token es inválido o expiró
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Busca al usuario en la BBDD usando el email (el 'sub' del token)
    user = db.query(models.User).filter(models.User.email == payload.get("sub")).first()
    
    if user is None:
        # Si el usuario del token ya no existe
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Si todo sale bien, devuelve el objeto User
    return user


# 5. El Endpoint Protegido (¡La Puerta Cerrada!)
@router.get("/me", response_model=schemas.User)
def read_users_me(
    # Esta es la magia: FastAPI ejecutará 'get_current_user' primero.
    # Si tiene éxito, nos pasará el usuario en la variable 'current_user'.
    # Si falla, lanzará el error 401 y este código nunca se ejecutará.
    current_user: models.User = Depends(get_current_user)
):
    """
    Devuelve la información del usuario actualmente autenticado.
    """
    return current_user

# -------------------------------------
# NUEVO: DEPENDENCIAS DE AUTORIZACIÓN (ROLES)
# -------------------------------------

def get_current_admin_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Dependencia que verifica que el usuario actual sea 'admin'.
    Si no lo es, lanza un error 403 Forbidden.
    """
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción. Se requiere ser Administrador."
        )
    return current_user

def get_current_medico_or_admin_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Dependencia que verifica que el usuario actual sea 'medico' O 'admin'.
    Si no lo es, lanza un error 403 Forbidden.
    """
    if current_user.role.name not in ("medico", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción. Se requiere ser Médico o Administrador."
        )
    return current_user