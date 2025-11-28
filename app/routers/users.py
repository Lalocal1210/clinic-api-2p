import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import SessionLocal

# Configuración de subida de imágenes
UPLOAD_DIR = "static/profile_pics"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Esquema de seguridad
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# --- DEPENDENCIAS ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> models.User:
    """
    Valida el token JWT y recupera el usuario actual.
    """
    payload = security.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_email = payload.get("sub")
    if user_email is None:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido (no contiene 'sub')",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# --- ENDPOINTS DE USUARIO ---

@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene la información del usuario logueado.
    """
    return current_user

@router.post("/me/photo", response_model=schemas.User)
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Sube una foto de perfil para el usuario actual.
    La guarda en 'static/profile_pics' y actualiza la URL en la BBDD.
    """
    
    # 1. Validar que sea una imagen
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida (png, jpg, jpeg).")
    
    # 2. Generar nombre único para evitar colisiones
    file_ext = file.filename.split('.')[-1]
    file_name = f"user_{current_user.id}_{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    # 3. Guardar el archivo físico
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la imagen: {e}")
    finally:
        await file.close()
        
    # 4. Actualizar la base de datos con la ruta relativa
    # Esta ruta es la que el frontend usará: http://.../static/profile_pics/nombre.jpg
    url_path = f"/static/profile_pics/{file_name}"
    
    current_user.profile_picture = url_path
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/doctors", response_model=List[schemas.User])
def get_doctors_list(db: Session = Depends(get_db)):
    """
    Lista pública de todos los médicos (rol ID 2).
    Usado para el selector en 'Agendar Cita'.
    """
    doctors = db.query(models.User).filter(models.User.role_id == 2).all()
    return doctors

@router.put("/me/change-password", response_model=schemas.Message)
def change_password(
    pass_in: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Cambio de contraseña para el usuario logueado.
    """
    # 1. Verificar la antigua
    if not security.verify_password(pass_in.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña antigua es incorrecta."
        )
        
    # 2. Validar longitud mínima
    if len(pass_in.new_password) < 4:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña es muy corta."
        )

    # 3. Actualizar
    new_hashed_password = security.get_password_hash(pass_in.new_password)
    current_user.password_hash = new_hashed_password
    
    db.commit()
    
    return {"detail": "Contraseña actualizada correctamente."}

# --- DEPENDENCIAS DE ROLES (Para usar en otros routers) ---

def get_current_admin_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Valida que el usuario sea Admin."""
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de Administrador."
        )
    return current_user

def get_current_medico_or_admin_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Valida que el usuario sea Médico o Admin."""
    if current_user.role.name not in ("medico", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes (Médico/Admin)."
        )
    return current_user