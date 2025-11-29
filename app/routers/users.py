import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, security
from ..database import SessionLocal

# 1. Creamos el "esquema" de seguridad
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 2. Creamos el router
router = APIRouter(
    prefix="/users",  # Todos los endpoints aquí empezarán con /users
    tags=["Users"]    # Los agrupa como "Users" en los /docs
)

# 3. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Dependencia de Seguridad (¡El Guardia Principal!)
def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> models.User:
    """
    Decodifica el token, encuentra al usuario en la BBDD y lo devuelve.
    Si algo falla (token inválido, usuario no existe), lanza un error 401.
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


# 5. El Endpoint Protegido (Ver mi propio perfil)
@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(get_current_user)
):
    """
    Devuelve la información del usuario actualmente autenticado.
    """
    return current_user

# 6. Endpoint Público para ver Médicos
@router.get(
    "/doctors", 
    response_model=List[schemas.User],
)
def get_doctors_list(db: Session = Depends(get_db)):
    """
    Obtiene una lista pública de todos los médicos (role_id=2).
    """
    doctors = db.query(models.User).filter(models.User.role_id == 2).all()
    return doctors

# 7. Endpoint Protegido (Cambiar mi propia contraseña)
@router.put("/me/change-password", response_model=schemas.Message)
def change_password(
    pass_in: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Permite al usuario autenticado cambiar su propia contraseña.
    """
    
    # 1. Verificar que la contraseña ANTIGUA sea correcta
    if not security.verify_password(pass_in.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña antigua es incorrecta."
        )
        
    # 2. Verificar que la nueva contraseña no esté vacía
    if not pass_in.new_password or len(pass_in.new_password) < 4:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña es muy corta."
        )

    # 3. Hashear y guardar la NUEVA contraseña
    new_hashed_password = security.get_password_hash(pass_in.new_password)
    current_user.password_hash = new_hashed_password
    
    db.commit()
    
    return {"detail": "Contraseña actualizada correctamente."}

# 8. Endpoint para SUBIR FOTO DE PERFIL (¡NUEVO!)
@router.post("/me/photo", response_model=schemas.User)
def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Sube una foto de perfil para el usuario actual (Médico, Admin o Paciente).
    """
    # 1. Validar que sea imagen
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    # 2. Crear directorio si no existe
    upload_dir = "static/profiles"
    os.makedirs(upload_dir, exist_ok=True)

    # 3. Generar nombre único
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"user_{current_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, file_name)

    # 4. Guardar archivo físico
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar imagen: {e}")
    finally:
        file.file.close()

    # 5. Actualizar base de datos (guardamos la URL relativa)
    # Usamos /static/profiles/... para que sea accesible web
    url_path = f"/static/profiles/{file_name}"
    
    current_user.profile_picture = url_path
    db.commit()
    db.refresh(current_user)
    
    return current_user


# -------------------------------------
# 9. DEPENDENCIAS DE AUTORIZACIÓN (ROLES)
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