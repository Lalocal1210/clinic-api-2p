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

# 3. Endpoint para CAMBIAR EL ROL de un usuario
@router.put("/users/{user_id}/role", response_model=schemas.User)
def update_user_role(
    user_id: int,
    role_in: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    # Verificamos que el que hace la petición es admin
    admin_user: models.User = Depends(get_current_admin_user)
):
    """
    Actualiza el rol de un usuario específico.
    Solo accesible para 'admin'.
    """
    
    # 1. Verificamos que el usuario a cambiar exista
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 2. Verificamos que el rol nuevo exista
    db_role = db.query(models.Role).filter(models.Role.id == role_in.role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="ID de Rol no encontrado")

    # 3. ¡Seguridad! Un admin no puede bajarse el rol a sí mismo por accidente
    if db_user.id == admin_user.id and role_in.role_id != 1:
        raise HTTPException(
            status_code=400, 
            detail="Un administrador no puede revocar sus propios privilegios."
        )

    # 4. Asignamos el nuevo rol y guardamos
    db_user.role_id = role_in.role_id
    db.commit()
    db.refresh(db_user)
    
    return db_user

# 4. Endpoint para LISTAR TODOS los usuarios
@router.get("/users", response_model=List[schemas.User])
def read_all_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Obtiene una lista de TODOS los usuarios del sistema.
    Solo accesible para 'admin'.
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users