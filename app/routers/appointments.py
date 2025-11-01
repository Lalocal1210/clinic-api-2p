# --- app/routers/appointments.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal
# Importamos TODOS nuestros "guardias" de seguridad
from .users import (
    get_current_user,
    get_current_medico_or_admin_user
)

# 1. Creamos el router
router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
    # ¡OJO! No ponemos una dependencia global
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
    ).all()
    
    return appointments

# 5. Endpoint para que MÉDICOS/ADMINS vean TODAS las citas
@router.get("/all", response_model=List[schemas.Appointment])
def read_all_appointments(
    db: Session = Depends(get_db),
    # ¡Protegido! Solo médicos o admins.
    current_user: models.User = Depends(get_current_medico_or_admin_user)
):
    """
    Obtiene una lista de TODAS las citas del sistema.
    Solo accesible para roles 'medico' o 'admin'.
    """
    appointments = db.query(models.Appointment).all()
    return appointments
# 6. Endpoint para ACTUALIZAR una cita
@router.put("/{appointment_id}", response_model=schemas.Appointment)
def update_appointment(
    appointment_id: int,
    appointment_in: schemas.AppointmentUpdate, # Usamos el nuevo schema
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Actualiza una cita.
    - Pacientes: Solo pueden actualizar sus propias citas.
    - Médicos/Admins: Pueden actualizar cualquier cita.
    """
    
    # 1. Busca la cita en la BBDD
    db_appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()
    
    # 2. Si no existe, 404
    if db_appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada."
        )
        
    # 3. Lógica de Permisos
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

    # 4. Actualiza los datos
    update_data = appointment_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_appointment, key, value)
        
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

# 7. Endpoint para ELIMINAR una cita
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
    
    # 1. Busca la cita
    db_appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()
    
    # 2. Si no existe, 404
    if db_appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada."
        )
        
    # 3. Lógica de Permisos (idéntica a la de actualizar)
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
        
    # 4. Elimina la cita
    db.delete(db_appointment)
    db.commit()
    
    return None # HTTP 204 No Content