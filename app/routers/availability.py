# --- app/routers/availability.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date, timedelta, time

from .. import models, schemas
from ..database import SessionLocal
# Importamos los dos guardias
from .users import get_current_medico_or_admin_user, get_current_user

router = APIRouter(
    prefix="/availability",
    tags=["Availability"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Endpoint para que el médico VEA su horario semanal
@router.get(
    "/me", 
    response_model=List[schemas.DoctorAvailability],
    dependencies=[Depends(get_current_medico_or_admin_user)] # Solo médicos/admins
)
def get_my_availability(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene el horario semanal guardado del médico actual.
    """
    availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == current_user.id
    ).order_by(models.DoctorAvailability.day_of_week).all()
    
    return availability


# 2. Endpoint para que el médico DEFINA su horario (Crear/Actualizar)
@router.post(
    "/set", 
    response_model=List[schemas.DoctorAvailability], # Devuelve el nuevo horario
    status_code=status.HTTP_201_CREATED
)
def set_availability(
    availabilities: List[schemas.DoctorAvailabilityCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_medico_or_admin_user)
):
    """
    Define el horario semanal del médico. 
    Borra el horario anterior y pone el nuevo.
    """
    # Borrar horario anterior
    db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == current_user.id
    ).delete()
    
    new_schedule = []
    # Crear nuevo horario
    for avail in availabilities:
        db_avail = models.DoctorAvailability(
            **avail.model_dump(),
            doctor_id=current_user.id
        )
        db.add(db_avail)
        new_schedule.append(db_avail)
    
    db.commit()
    
    # Devolvemos los objetos recién creados
    return new_schedule


# 3. Endpoint para ver los horarios disponibles (Slots)
@router.get("/slots", response_model=List[schemas.TimeSlot])
def get_available_slots(
    doctor_id: int,
    query_date: date,
    db: Session = Depends(get_db)
):
    """
    Calcula los horarios disponibles para un médico en una fecha específica.
    Intervalos de 30 minutos.
    """
    # A. Verificar Horario Base (Ej. Lunes 9-17)
    day_of_week = query_date.weekday() # 0=Lunes
    
    availability = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == doctor_id,
        models.DoctorAvailability.day_of_week == day_of_week,
        models.DoctorAvailability.is_active == True # Asegurarse de que el día esté activo
    ).first()
    
    if not availability:
        return [] # El médico no trabaja este día
        
    # B. Obtener Citas Existentes de ese día
    start_of_day = datetime.combine(query_date, time.min)
    end_of_day = datetime.combine(query_date, time.max)
    
    existing_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date >= start_of_day,
        models.Appointment.appointment_date <= end_of_day,
        models.Appointment.status_id.in_([1, 2]) # 1=pendiente, 2=confirmada
    ).all()
    
    booked_times = [app.appointment_date.time() for app in existing_appointments]
    
    # C. Generar Slots de 30 mins
    slots = []
    current_time = datetime.combine(query_date, availability.start_time)
    end_time = datetime.combine(query_date, availability.end_time)
    
    while current_time < end_time:
        slot_time = current_time.time()
        
        is_taken = False
        for booked in booked_times:
            if booked.hour == slot_time.hour and booked.minute == slot_time.minute:
                is_taken = True
                break
        
        is_past = False
        if query_date == date.today() and slot_time < datetime.now().time():
            is_past = True

        if not is_taken and not is_past:
            slots.append(schemas.TimeSlot(
                time=slot_time.strftime("%H:%M"),
                is_available=True
            ))
            
        current_time += timedelta(minutes=30) 
        
    return slots