# --- app/routers/settings.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal
# Importamos el guardia de usuario logueado
from .users import get_current_user

# 1. Creamos el router
router = APIRouter(
    prefix="/settings",
    tags=["User Settings"],
    # Protegemos TODOS los endpoints de este router
    dependencies=[Depends(get_current_user)]
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Endpoint para OBTENER la configuración del usuario
@router.get("/me", response_model=schemas.UserSettings)
def get_my_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene la configuración del usuario actual.
    Si no existe, la crea con los valores por defecto.
    """
    
    # 1. Buscamos la configuración del usuario
    settings = db.query(models.UserSettings).filter(
        models.UserSettings.user_id == current_user.id
    ).first()
    
    # 2. Si no existe, la creamos
    if not settings:
        new_settings = models.UserSettings(
            user_id=current_user.id
            # Los valores por defecto (dark_mode=False, etc.)
            # se aplican automáticamente desde el modelo
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings
        
    # 3. Si existe, la devolvemos
    return settings

# 4. Endpoint para ACTUALIZAR la configuración del usuario
@router.put("/me", response_model=schemas.UserSettings)
def update_my_settings(
    settings_in: schemas.UserSettingsBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Actualiza la configuración (ej. modo oscuro) del usuario actual.
    """
    
    # 1. Buscamos la configuración (debería existir por el GET)
    db_settings = db.query(models.UserSettings).filter(
        models.UserSettings.user_id == current_user.id
    ).first()
    
    if not db_settings:
        # Esto no debería pasar si el usuario ha llamado a GET /me primero
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    # 2. Actualizamos los datos
    # model_dump() convierte el Pydantic (settings_in) a un diccionario
    update_data = settings_in.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_settings, key, value)
        
    db.commit()
    db.refresh(db_settings)
    return db_settings