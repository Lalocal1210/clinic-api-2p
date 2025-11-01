# --- app/routers/dashboard.py ---

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal
# ¡Importamos el guardia! Solo médicos y admins pueden ver el dashboard
from .users import get_current_medico_or_admin_user

# 1. Creamos el router
router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    # Protegemos este endpoint
    dependencies=[Depends(get_current_medico_or_admin_user)]
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. El Endpoint del Dashboard
@router.get("/", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    # Obtenemos al médico que está pidiendo los datos
    current_user: models.User = Depends(get_current_medico_or_admin_user)
):
    """
    Obtiene las métricas clave para el dashboard del médico.
    """
    
    # Lógica de "Hoy"
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    # --- Hacemos las 3 consultas a la BBDD ---

    # 1. Total de pacientes (en todo el sistema)
    total_patients = db.query(models.Patient).count()

    # 2. Citas próximas (del médico actual, que estén 'pendientes' o 'confirmadas')
    upcoming_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == current_user.id,
        models.Appointment.appointment_date > datetime.now(),
        models.Appointment.status_id.in_([1, 2]) # 1=pendiente, 2=confirmada
    ).count()

    # 3. Citas completadas HOY (por el médico actual)
    completed_appointments_today = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == current_user.id,
        models.Appointment.appointment_date.between(today_start, today_end),
        models.Appointment.status_id == 3 # 3=completada
    ).count()

    # 4. Devolvemos el objeto
    return schemas.DashboardMetrics(
        total_patients=total_patients,
        upcoming_appointments=upcoming_appointments,
        completed_appointments_today=completed_appointments_today
    )