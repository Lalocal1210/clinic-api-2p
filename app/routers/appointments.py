from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .. import models, schemas
from ..database import SessionLocal

# Importamos guardias
from .users import get_current_user, get_current_medico_or_admin_user

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. CREAR CITA (Paciente) -> ¡AHORA NOTIFICA AL MÉDICO!
@router.post("/", response_model=schemas.Appointment, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_in: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    """
    Crea una nueva cita y NOTIFICA AL MÉDICO automáticamente.
    """
    if current_user.role.name != "paciente" or not current_user.patient_profile:
        raise HTTPException(status_code=403, detail="Solo pacientes pueden agendar.")

    # Crear la cita
    new_appointment = models.Appointment(
        **appointment_in.model_dump(),
        patient_id=current_user.patient_profile.id,
        status_id=1 # Pendiente
    )
    
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    # --- ¡CORRECCIÓN: NOTIFICAR AL MÉDICO! ---
    # Buscamos al doctor para usar su nombre si es necesario, pero sobre todo su ID
    # El 'user_id' de la notificación debe ser el ID del DOCTOR.
    
    fecha_formato = new_appointment.appointment_date.strftime("%d/%m a las %H:%M")
    
    notification = models.Notification(
        user_id=appointment_in.doctor_id, # <--- Al Médico
        type_id=1, # Tipo 'Recordatorio/Solicitud'
        message=f"Nueva solicitud de cita: {current_user.full_name} para el {fecha_formato}.",
        is_read=False,
        created_at=datetime.now()
    )
    db.add(notification)
    db.commit()
    # -----------------------------------------

    return new_appointment

# 2. VER MIS CITAS (Paciente)
@router.get("/me", response_model=List[schemas.Appointment])
def read_my_appointments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.patient_profile:
        raise HTTPException(status_code=404, detail="Perfil de paciente no encontrado.")
    
    return db.query(models.Appointment).filter(
        models.Appointment.patient_id == current_user.patient_profile.id
    ).order_by(models.Appointment.appointment_date.desc()).all()

# 3. VER TODAS (Médico/Admin)
@router.get("/all", response_model=List[schemas.Appointment], dependencies=[Depends(get_current_medico_or_admin_user)])
def read_all_appointments(db: Session = Depends(get_db)):
    return db.query(models.Appointment).order_by(models.Appointment.appointment_date.desc()).all()

# 4. ACTUALIZAR CITA (Datos)
@router.put("/{appointment_id}", response_model=schemas.Appointment)
def update_appointment(
    appointment_id: int,
    appointment_in: schemas.AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_appointment = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
        
    # Permisos simplificados para brevedad (manteniendo tu lógica original)
    is_auth = (current_user.role.name in ["admin", "medico"]) or \
              (current_user.patient_profile and db_appointment.patient_id == current_user.patient_profile.id)
    
    if not is_auth:
        raise HTTPException(status_code=403, detail="Sin permisos.")

    for key, value in appointment_in.model_dump(exclude_unset=True).items():
        setattr(db_appointment, key, value)
        
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

# 5. ELIMINAR/CANCELAR CITA
@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_appointment = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    
    # --- NOTIFICAR AL MÉDICO SI EL PACIENTE BORRA ---
    # Si quien borra es el paciente, le avisamos al doctor
    if current_user.patient_profile and db_appointment.patient_id == current_user.patient_profile.id:
        notif = models.Notification(
            user_id=db_appointment.doctor_id, # Al Doctor
            type_id=2, # Tipo 'Aviso'
            message=f"El paciente {current_user.full_name} canceló/eliminó su cita.",
            is_read=False,
            created_at=datetime.now()
        )
        db.add(notif)
        # No hacemos commit aquí, se hace abajo con el delete
    # -----------------------------------------------
        
    db.delete(db_appointment)
    db.commit()
    return None

# 6. CAMBIAR ESTADO (Médico confirma/cancela) -> Notifica al PACIENTE
@router.patch("/{appointment_id}/status", response_model=schemas.Appointment, dependencies=[Depends(get_current_medico_or_admin_user)])
def update_appointment_status(
    appointment_id: int,
    status_in: schemas.AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_medico_or_admin_user)
):
    db_appointment = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")

    if status_in.status_id == 4 and not status_in.cancellation_reason:
        raise HTTPException(status_code=400, detail="Motivo requerido para cancelar.")

    db_appointment.status_id = status_in.status_id
    
    # --- Lógica de Notificación al PACIENTE ---
    msg = ""
    type_id = 1
    
    if status_in.status_id == 2: # Confirmada
        db_appointment.cancellation_reason = None
        msg = f"¡Tu cita ha sido CONFIRMADA por el Dr. {current_user.full_name}!"
        type_id = 2
    elif status_in.status_id == 4: # Cancelada
        db_appointment.cancellation_reason = status_in.cancellation_reason
        msg = f"Tu cita fue CANCELADA. Motivo: {status_in.cancellation_reason}"
        type_id = 3

    db.commit() # Guardamos el cambio de estado primero

    # Si hay mensaje y el paciente tiene usuario, creamos la notificación
    if msg and db_appointment.patient.user_id:
        new_notif = models.Notification(
            user_id=db_appointment.patient.user_id, # Al Paciente
            type_id=type_id,
            message=msg,
            is_read=False,
            created_at=datetime.now()
        )
        db.add(new_notif)
        db.commit()

    db.refresh(db_appointment)
    return db_appointment