from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal

# Importamos el guardia de seguridad (Médicos o Admins)
from .users import get_current_medico_or_admin_user

# 1. Creamos el router
router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    # Protegemos este endpoint para que solo entren médicos o admins
    dependencies=[Depends(get_current_medico_or_admin_user)]
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. El Endpoint del Dashboard Inteligente
@router.get("/", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    # Obtenemos al usuario que está pidiendo los datos
    current_user: models.User = Depends(get_current_medico_or_admin_user)
):
    """
    Obtiene las métricas clave para el dashboard.
    - Si es ADMIN: Devuelve estadísticas globales de la clínica.
    - Si es MÉDICO: Devuelve estadísticas de su propia agenda.
    """
    
    # Definimos el rango de tiempo para "Hoy"
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    # --- MÉTRICA COMÚN: Total de Pacientes ---
    # Ambos roles necesitan saber cuántos pacientes hay en el sistema
    total_patients = db.query(models.Patient).count()

    # ==========================================
    # CASO 1: ADMINISTRADOR (Visión Global)
    # ==========================================
    if current_user.role.name == 'admin':
        
        # 1. Citas Totales Hoy (De todos los doctores)
        total_appointments_today = db.query(models.Appointment).filter(
            models.Appointment.appointment_date.between(today_start, today_end)
        ).count()
        
        # 2. Usuarios Totales (Para medir crecimiento de la app)
        total_users = db.query(models.User).count()
        
        # 3. Doctores Activos (Usuarios con rol 2 y activos)
        active_doctors = db.query(models.User).filter(
            models.User.role_id == 2, 
            models.User.is_active == True
        ).count()
        
        # Devolvemos el objeto lleno con datos de Admin y vacíos los de Médico
        return schemas.DashboardMetrics(
            total_patients=total_patients,
            total_appointments_today=total_appointments_today,
            total_users=total_users,
            active_doctors=active_doctors,
            # Campos específicos de médico van en 0 o None
            upcoming_appointments=0,
            completed_appointments_today=0
        )

    # ==========================================
    # CASO 2: MÉDICO (Visión Personal)
    # ==========================================
    else:
        # 1. Citas Próximas (Del futuro y que no estén canceladas/completadas)
        upcoming_appointments = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == current_user.id,
            models.Appointment.appointment_date > datetime.now(),
            models.Appointment.status_id.in_([1, 2]) # 1=pendiente, 2=confirmada
        ).count()

        # 2. Citas Completadas HOY (Productividad diaria)
        completed_appointments_today = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == current_user.id,
            models.Appointment.appointment_date.between(today_start, today_end),
            models.Appointment.status_id == 3 # 3=completada
        ).count()

        # Devolvemos el objeto lleno con datos de Médico y vacíos los de Admin
        return schemas.DashboardMetrics(
            total_patients=total_patients,
            upcoming_appointments=upcoming_appointments,
            completed_appointments_today=completed_appointments_today,
            # Campos específicos de admin van en 0
            total_appointments_today=0,
            total_users=0,
            active_doctors=0
        )