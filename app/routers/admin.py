from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import SessionLocal
from .users import get_current_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. LISTAR USUARIOS ---
@router.get("/users", response_model=List[schemas.User])
def read_all_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    users = db.query(models.User).order_by(models.User.full_name.asc()).offset(skip).limit(limit).all()
    return users

# --- 2. CAMBIAR ROL ---
@router.put("/users/{user_id}/role", response_model=schemas.User)
def update_user_role(
    user_id: int,
    role_in: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if db_user.id == admin_user.id and role_in.role_id != 1:
        raise HTTPException(status_code=400, detail="No puedes quitarte tu propio rol de admin.")

    db_user.role_id = role_in.role_id
    db.commit()
    db.refresh(db_user)
    return db_user

# --- 3. ACTIVAR/DESACTIVAR ---
@router.patch("/users/{user_id}/status", response_model=schemas.User)
def update_user_status(
    user_id: int,
    status_in: schemas.UserStatusUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if db_user.id == admin_user.id and not status_in.is_active:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo.")

    db_user.is_active = status_in.is_active
    db.commit()
    db.refresh(db_user)
    return db_user

# --- 4. ¡AQUÍ ESTÁ LA FUNCIÓN QUE FALTABA! EDITAR DATOS ---
@router.put("/users/{user_id}", response_model=schemas.User)
def update_user_details(
    user_id: int,
    user_in: schemas.UserAdminUpdate,
    db: Session = Depends(get_db)
):
    """
    Permite al admin cambiar nombre, email o teléfono.
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizar solo los campos que vienen en el request
    update_data = user_in.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_user, key, value)

    # Si cambiamos el nombre en User, también actualizamos el perfil de Paciente si existe
    if db_user.patient_profile:
        if 'full_name' in update_data:
            db_user.patient_profile.full_name = update_data['full_name']
        if 'email' in update_data:
            db_user.patient_profile.email = update_data['email']
        if 'phone' in update_data:
            db_user.patient_profile.phone = update_data['phone']

    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al actualizar. Posible email duplicado.")

# --- 5. ELIMINAR ---
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_current_admin_user)
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if db_user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo.")

    db.delete(db_user)
    db.commit()
    return None