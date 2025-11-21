from pydantic import BaseModel, EmailStr
from datetime import date, datetime, time 

# -----------------
# 1. Esquemas de Catálogos y Autenticación
# -----------------

class RoleBase(BaseModel):
    name: str
    description: str | None = None

class Role(RoleBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class AppointmentStatusBase(BaseModel):
    name: str
    description: str | None = None

class AppointmentStatus(AppointmentStatusBase):
    id: int
    class Config:
        from_attributes = True

# -----------------
# 2. Esquema del Dashboard
# -----------------

class DashboardMetrics(BaseModel):
    """Esquema para los datos del dashboard del médico."""
    total_patients: int
    upcoming_appointments: int
    completed_appointments_today: int
    
    class Config:
        from_attributes = True

# -----------------
# 3. Esquemas de Direcciones
# -----------------

class AddressBase(BaseModel):
    street: str
    city: str
    state: str | None = None
    postal_code: str | None = None
    country: str = 'México'
    address_type: str = 'home'

class AddressCreate(AddressBase):
    pass

class Address(AddressBase):
    id: int
    class Config:
        from_attributes = True

# -----------------
# 4. Esquemas Base para CREAR y ACTUALIZAR
# -----------------

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    password: str 
    # --- ¡CAMBIO AQUÍ! ---
    birth_date: date | None = None # <--- AGREGADO: Necesario para el registro

class RoleUpdate(BaseModel):
    """Esquema para actualizar el rol de un usuario (Admin)."""
    role_id: int

class UserStatusUpdate(BaseModel):
    """Esquema para activar o desactivar un usuario."""
    is_active: bool

class PatientBase(BaseModel):
    full_name: str
    gender: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None

class PatientCreate(PatientBase):
    pass

# --- Esquemas de Actualización de Paciente ---

class PatientProfileUpdate(BaseModel):
    """
    Esquema para que el PACIENTE actualice su propio perfil.
    (No incluye género, nombre, email ni fecha de nacimiento).
    """
    phone: str | None = None
    
    # Médicos
    allergies: str | None = None
    current_medications: str | None = None
    chronic_conditions: str | None = None
    blood_type: str | None = None
    height_cm: int | None = None

    # Emergencia
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    
    # Personal
    marital_status: str | None = None

class PatientAdminUpdate(PatientProfileUpdate):
    """
    Esquema para que el ADMIN/MÉDICO actualice un perfil.
    Hereda todo lo del paciente Y ADEMÁS permite editar datos sensibles.
    """
    full_name: str | None = None
    email: EmailStr | None = None
    gender: str | None = None
    birth_date: date | None = None # Admin sí puede editar fecha

class AppointmentBase(BaseModel):
    appointment_date: datetime
    reason: str | None = None
    
class AppointmentCreate(AppointmentBase):
    doctor_id: int

class AppointmentUpdate(BaseModel):
    appointment_date: datetime | None = None
    reason: str | None = None
    doctor_id: int | None = None
    status_id: int | None = None

class AppointmentStatusUpdate(BaseModel):
    """Esquema para confirmar/cancelar citas."""
    status_id: int 
    cancellation_reason: str | None = None 

class MedicalNoteBase(BaseModel):
    title: str
    content: str
    appointment_id: int | None = None 

class MedicalNoteCreate(MedicalNoteBase):
    pass

class MedicalNoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    appointment_id: int | None = None

class VitalSignBase(BaseModel):
    type_name: str
    value: str
    unit: str | None = None
    measured_at: datetime | None = datetime.now()

class VitalSignCreate(VitalSignBase):
    pass

class VitalSignUpdate(BaseModel):
    type_name: str | None = None
    value: str | None = None
    unit: str | None = None
    measured_at: datetime | None = None

class MedicalFileBase(BaseModel):
    description: str | None = None

class UserSettingsBase(BaseModel):
    dark_mode: bool = False
    language: str = 'es'
    notifications_enabled: bool = True

class NotificationBase(BaseModel):
    message: str
    is_read: bool

# --- Esquemas de Seguridad ---
class PasswordChange(BaseModel):
    """Esquema para cambiar la contraseña."""
    old_password: str
    new_password: str

class Message(BaseModel):
    """Esquema para un mensaje de respuesta simple."""
    detail: str

# --- ¡NUEVOS ESQUEMAS DE DISPONIBILIDAD! ---

class DoctorAvailabilityBase(BaseModel):
    day_of_week: int # 0=Lunes, ... 6=Domingo
    start_time: time # 09:00:00
    end_time: time   # 17:00:00

class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    pass

class DoctorAvailability(DoctorAvailabilityBase):
    id: int
    doctor_id: int
    class Config:
        from_attributes = True

class BlockedTimeBase(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None = None

class BlockedTimeCreate(BlockedTimeBase):
    pass

class BlockedTime(BlockedTimeBase):
    id: int
    doctor_id: int
    class Config:
        from_attributes = True

class TimeSlot(BaseModel):
    """Esquema para devolver un horario disponible al frontend"""
    time: str # "09:00"
    is_available: bool

# -----------------
# 5. Esquemas Simples y Públicos (Anidados)
# -----------------

class PatientSimple(BaseModel):
    """Perfil simple de paciente para mostrar anidado"""
    id: int
    full_name: str
    class Config:
        from_attributes = True

class AppointmentSimple(BaseModel):
    """Esquema simple de cita para mostrar anidado"""
    id: int
    appointment_date: datetime
    reason: str | None = None
    class Config:
        from_attributes = True

class UserPublic(UserBase):
    """
    Esquema de Usuario que INCLUYE el ID.
    Se usa para mostrar la info del doctor dentro de una cita.
    """
    id: int
    class Config:
        from_attributes = True

# -----------------
# 6. Esquemas Completos (para LEER)
# -----------------

class MedicalNote(MedicalNoteBase):
    id: int
    created_at: datetime
    doctor: UserPublic 
    patient_id: int 
    class Config:
        from_attributes = True

class VitalSign(VitalSignBase):
    id: int
    patient_id: int
    doctor: UserPublic | None = None 
    class Config:
        from_attributes = True

class MedicalFile(MedicalFileBase):
    id: int
    file_path: str 
    uploaded_at: datetime
    uploader: UserPublic
    class Config:
        from_attributes = True

class User(UserBase):
    """Esquema 'User' completo"""
    id: int
    is_active: bool
    role: Role 
    patient_profile: PatientSimple | None = None 
    class Config:
        from_attributes = True

class Patient(PatientBase):
    """Esquema 'Patient' completo"""
    id: int
    addresses: list[Address] = []       
    appointments: list[AppointmentSimple] = [] 
    medical_notes: list[MedicalNote] = []
    vital_signs: list[VitalSign] = []
    files: list[MedicalFile] = []
    temporary_password: str | None = None 
    
    # --- Campos de perfil extendido ---
    allergies: str | None = None
    current_medications: str | None = None
    chronic_conditions: str | None = None
    blood_type: str | None = None
    height_cm: int | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    marital_status: str | None = None
    
    class Config:
        from_attributes = True

class Appointment(AppointmentBase):
    """Esquema 'Appointment' completo"""
    id: int
    patient: PatientSimple      
    doctor: UserPublic          
    status: AppointmentStatus   
    cancellation_reason: str | None = None
    class Config:
        from_attributes = True

class UserSettings(UserSettingsBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

class Notification(NotificationBase):
    id: int
    created_at: datetime
    type_name: str
    class Config:
        from_attributes = True