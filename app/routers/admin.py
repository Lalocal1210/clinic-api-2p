# --- app/routers/admin.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal
# ¡Importamos el guardia MÁS FUERTE!
from .users import get_current_admin_user

# 1. Creamos el router
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    # ¡MÁXIMA SEGURIDAD!
    # Todos los endpoints en este archivo requerirán ser admin.
    dependencies=[Depends(get_current_admin_user)]
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Endpoint para LISTAR TODOS los usuarios
@router.get("/users", response_model=List[schemas.User])
def read_all_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Obtiene una lista paginada de TODOS los usuarios del sistema.
    Solo accesible para 'admin'.
    """
    users = db.query(models.User).order_by(models.User.full_name.asc()).offset(skip).limit(limit).all()
    return users

# 4. Endpoint para CAMBIAR EL ROL de un usuario
@router.put("/users/{user_id}/role", response_model=schemas.User)
def update_user_role(
    user_id: int,
    role_in: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    """
    Actualiza el rol de un usuario específico (ej. Paciente -> Médico).
    Solo accesible para 'admin'.
    """
    
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db_role = db.query(models.Role).filter(models.Role.id == role_in.role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="ID de Rol no encontrado")

    # Seguridad: Un admin no puede bajarse el rol a sí mismo
    if db_user.id == admin_user.id and role_in.role_id != 1: # 1 = ID de Admin
        raise HTTPException(
            status_code=400, 
            detail="Un administrador no puede revocar sus propios privilegios."
        )

    db_user.role_id = role_in.role_id
    db.commit()
    db.refresh(db_user)
    
    return db_user

# 5. Endpoint para DESACTIVAR/REACTIVAR un usuario
@router.patch("/users/{user_id}/status", response_model=schemas.User)
def update_user_status(
    user_id: int,
    status_in: schemas.UserStatusUpdate, # Usa el schema { "is_active": true/false }
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    """
    Activa o desactiva la cuenta de un usuario.
    Solo accesible para 'admin'.
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Seguridad: Un admin no puede desactivarse a sí mismo
    if db_user.id == admin_user.id and not status_in.is_active:
        raise HTTPException(
            status_code=400, 
            detail="Un administrador no puede desactivar su propia cuenta."
        )

    db_user.is_active = status_in.is_active
    db.commit()
    db.refresh(db_user)
    
    return db_user

# 6. Endpoint para ELIMINAR un usuario
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    """
    Elimina un usuario específico del sistema (y todos sus datos en cascada).
    Solo accesible para 'admin'.
    """
    
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Seguridad: Un admin no puede borrarse a sí mismo
    if db_user.id == admin_user.id:
        raise HTTPException(
            status_code=400, 
            detail="Un administrador no puede eliminarse a sí mismo."
        )

    # Eliminar el usuario
    # (El 'cascade' en models.py se encarga de borrar
    # el patient_profile, citas, notas, etc., vinculadas a este User)
    db.delete(db_user)
    db.commit()
    
    return None # HTTP 204 No Content
