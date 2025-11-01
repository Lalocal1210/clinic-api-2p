# --- app/routers/notifications.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal
# Importamos el guardia de usuario logueado
from .users import get_current_user

# 1. Creamos el router
router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
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

# 3. Endpoint para OBTENER las notificaciones del usuario
@router.get("/me", response_model=List[schemas.Notification])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False # Opción para filtrar solo no leídas
):
    """
    Obtiene las notificaciones del usuario actual.
    """
    query = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(models.Notification.is_read == False)
        
    notifications = query.order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    # Adaptamos el resultado al esquema (aplanando el type_name)
    result = []
    for notif in notifications:
        result.append(schemas.Notification(
            id=notif.id,
            message=notif.message,
            is_read=notif.is_read,
            created_at=notif.created_at,
            type_name=notif.notification_type.name # Aplanamos aquí
        ))
        
    return result

# 4. Endpoint para MARCAR una notificación como leída
@router.patch("/{notification_id}/read", response_model=schemas.Notification)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Marca una notificación específica del usuario actual como leída.
    """
    # Buscamos la notificación
    db_notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id # Asegura que es SU notificación
    ).first()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
        
    # La marcamos como leída
    db_notification.is_read = True
    db.commit()
    db.refresh(db_notification)
    
    # Adaptamos al schema
    return schemas.Notification(
        id=db_notification.id,
        message=db_notification.message,
        is_read=db_notification.is_read,
        created_at=db_notification.created_at,
        type_name=db_notification.notification_type.name
    )

# 5. Endpoint para BORRAR una notificación
@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Elimina una notificación específica del usuario actual.
    """
    # Buscamos la notificación
    db_notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id # Asegura que es SU notificación
    ).first()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
        
    # La eliminamos
    db.delete(db_notification)
    db.commit()
    
    # HTTP 204 No Content no devuelve cuerpo
    return None