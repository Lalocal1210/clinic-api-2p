# --- app/routers/appointments.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal, engine
# Importamos TODOS nuestros "guardias" de seguridad
from .users import (
    get_current_user,
    get_current_medico_or_admin_user
)

# 1. Creamos el router
router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
    # No ponemos una dependencia global
    # porque este router tiene permisos MIXTOS.
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Endpoint para que un PACIENTE cree su cita
@router.post("/", response_model=schemas.Appointment, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_in: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    # ¡Protegido! Solo un usuario logueado puede crear una cita.
    current_user: models.User = Depends(get_current_user) 
):
    """
    Crea una nueva cita.
    Un paciente solo puede crear citas para sí mismo.
    """
    
    # Verificamos que el usuario que crea la cita sea un paciente
    if current_user.role.name != "paciente" or not current_user.patient_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios de tipo 'paciente' pueden agendar citas."
        )

    # Creamos el objeto de la cita
    new_appointment = models.Appointment(
        **appointment_in.model_dump(),
        patient_id=current_user.patient_profile.id, # ¡Se asigna a sí mismo!
        status_id=1 # Por defecto: 1 = 'pendiente'
    )
    
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return new_appointment

# 4. Endpoint para que un PACIENTE vea SUS citas
@router.get("/me", response_model=List[schemas.Appointment])
def read_my_appointments(
    db: Session = Depends(get_db),
    # ¡Protegido!
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene la lista de citas del paciente actualmente autenticado.
    """
    if not current_user.patient_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este usuario no tiene un perfil de paciente asociado."
        )
    
    # Buscamos las citas que le pertenecen a este paciente
    appointments = db.query(models.Appointment).filter(
        models.Appointment.patient_id == current_user.patient_profile.id
    ).order_by(models.Appointment.appointment_date.desc()).all()
    
    return appointments

# 5. Endpoint para que MÉDICOS/ADMINS vean TODAS las citas
@router.get(
    "/all", 
    response_model=List[schemas.Appointment],
    # ¡Protegido! Solo médicos o admins.
    dependencies=[Depends(get_current_medico_or_admin_user)]
)
def read_all_appointments(
    db: Session = Depends(get_db)
):
    """
    Obtiene una lista de TODAS las citas del sistema.
    Solo accesible para roles 'medico' o 'admin'.
    """
    appointments = db.query(models.Appointment).order_by(models.Appointment.appointment_date.desc()).all()
    return appointments

# 6. Endpoint para ACTUALIZAR una cita (permisos mixtos)
@router.put("/{appointment_id}", response_model=schemas.Appointment)
def update_appointment(
    appointment_id: int,
    appointment_in: schemas.AppointmentUpdate, # Usamos el schema de actualización
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Actualiza una cita.
    - Pacientes: Solo pueden actualizar sus propias citas.
    - Médicos/Admins: Pueden actualizar cualquier cita.
    """
    
    db_appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()
    
    if db_appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada."
        )
        
    # Lógica de Permisos
    is_admin_or_medico = current_user.role.name in ("admin", "medico")
    is_patient_owner = (
        current_user.patient_profile and 
        db_appointment.patient_id == current_user.patient_profile.id
    )
    
    if not is_admin_or_medico and not is_patient_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar esta cita."
        )

    # Actualiza los datos
    update_data = appointment_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_appointment, key, value)
        
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

# 7. Endpoint para ELIMINAR una cita (permisos mixtos)
@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Elimina una cita.
    - Pacientes: Solo pueden eliminar sus propias citas.
    - Médicos/Admins: Pueden eliminar cualquier cita.
    """
    
    db_appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()
    
    if db_appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada."
        )
        
    # Lógica de Permisos (idéntica a la de actualizar)
    is_admin_or_medico = current_user.role.name in ("admin", "medico")
    is_patient_owner = (
        current_user.patient_profile and 
        db_appointment.patient_id == current_user.patient_profile.id
    )
    
    if not is_admin_or_medico and not is_patient_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para eliminar esta cita."
        )
        
    db.delete(db_appointment)
    db.commit()
    
    return None # HTTP 204 No Content

# 8. Endpoint (Médico) para CAMBIAR EL ESTADO de una cita (¡ACTUALIZADO!)
@router.patch(
    "/{appointment_id}/status", 
    response_model=schemas.Appointment,
    # ¡Protegido! Solo médicos o admins
    dependencies=[Depends(get_current_medico_or_admin_user)] 
)
def update_appointment_status(
    appointment_id: int,
    status_in: schemas.AppointmentStatusUpdate, # Usamos el schema actualizado
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_medico_or_admin_user) # Obtenemos al médico
):
    """
    Actualiza el estado de una cita (ej. pendiente -> confirmada).
    Si se cancela (ID 4), se debe incluir un 'cancellation_reason'.
    ¡Envía una notificación automática al paciente!
    """
    
    # 1. Busca la cita
    db_appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()
    
    if db_appointment is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
        
    # 2. Verifica que el nuevo status_id sea válido
    db_status = db.query(models.AppointmentStatus).filter(
        models.AppointmentStatus.id == status_in.status_id
    ).first()
    
    if db_status is None:
        raise HTTPException(status_code=400, detail=f"El ID de estado '{status_in.status_id}' no es válido.")

    # 3. ¡Lógica de Negocio!
    # Si el nuevo estado es "cancelada" (ID 4), exige un motivo.
    if status_in.status_id == 4 and not status_in.cancellation_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere un 'cancellation_reason' para cancelar una cita."
        )

    # 4. Actualiza la cita
    db_appointment.status_id = status_in.status_id
    notification_message = ""
    # Asumimos que el tipo 1='Recordatorio', 2='Resultado/Aviso', 3='Mensaje Médico'
    notification_type = 1 
    
    if status_in.status_id == 2: # 2 = Confirmada
        db_appointment.cancellation_reason = None # Borra el motivo si se re-confirma
        notification_message = f"¡Buenas noticias! Tu cita para '{db_appointment.reason}' ha sido confirmada por el Dr. {current_user.full_name}."
        notification_type = 2
        
    elif status_in.status_id == 4: # 4 = Cancelada
        db_appointment.cancellation_reason = status_in.cancellation_reason
        notification_message = f"Tu cita para '{db_appointment.reason}' ha sido cancelada. Motivo: {status_in.cancellation_reason}"
        notification_type = 3

    db.commit()

    # 5. ¡Crea la Notificación Automática!
    # (Solo si se confirmó o canceló y si el paciente tiene una cuenta de usuario)
    if (status_in.status_id == 2 or status_in.status_id == 4) and db_appointment.patient.user_id:
        new_notification = models.Notification(
            user_id=db_appointment.patient.user_id,
            type_id=notification_type,
            message=notification_message
        )
        db.add(new_notification)
        db.commit() # Guarda la notificación

    db.refresh(db_appointment)
    return db_appointment