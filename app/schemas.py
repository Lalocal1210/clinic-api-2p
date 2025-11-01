# --- app/schemas.py ---

from pydantic import BaseModel, EmailStr
from datetime import date, datetime

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
# 2. Esquemas de Direcciones
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
# 3. Esquemas Base para CREAR y ACTUALIZAR
# -----------------

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    password: str 

class PatientBase(BaseModel):
    full_name: str
    gender: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    """
    Esquema para ACTUALIZAR un Paciente.
    Todos los campos son opcionales.
    """
    full_name: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None

class AppointmentBase(BaseModel):
    appointment_date: datetime
    reason: str | None = None
    
class AppointmentCreate(AppointmentBase):
    doctor_id: int

class MedicalNoteBase(BaseModel):
    title: str
    content: str
    appointment_id: int | None = None  # Opcional

class MedicalNoteCreate(MedicalNoteBase):
    pass

class VitalSignBase(BaseModel):
    type_name: str
    value: str
    unit: str | None = None
    measured_at: datetime | None = datetime.now()

class VitalSignCreate(VitalSignBase):
    pass

# --- NUEVOS ESQUEMAS PARA ACTUALIZAR ---

class MedicalNoteUpdate(BaseModel):
    """Esquema para ACTUALIZAR una nota. Todos los campos opcionales."""
    title: str | None = None
    content: str | None = None
    appointment_id: int | None = None

class VitalSignUpdate(BaseModel):
    """Esquema para ACTUALIZAR un signo vital. Todos los campos opcionales."""
    type_name: str | None = None
    value: str | None = None
    unit: str | None = None
    measured_at: datetime | None = None

# -----------------
# 4. Esquemas Simples
# -----------------

class PatientSimple(BaseModel):
    id: int
    full_name: str
    class Config:
        from_attributes = True

class AppointmentSimple(BaseModel):
    id: int
    appointment_date: datetime
    reason: str | None = None
    class Config:
        from_attributes = True

# -----------------
# 5. Esquemas Completos (para LEER)
# -----------------

class MedicalNote(MedicalNoteBase):
    id: int
    created_at: datetime
    doctor: UserBase
    patient_id: int 
    class Config:
        from_attributes = True

class VitalSign(VitalSignBase):
    id: int
    patient_id: int
    doctor: UserBase | None = None
    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    is_active: bool
    role: Role 
    patient_profile: PatientSimple | None = None
    class Config:
        from_attributes = True

class Patient(PatientBase):
    id: int
    addresses: list[Address] = []       
    appointments: list[AppointmentSimple] = [] 
    medical_notes: list[MedicalNote] = []
    vital_signs: list[VitalSign] = []
    class Config:
        from_attributes = True

class Appointment(AppointmentBase):
    id: int
    patient: PatientSimple
    doctor: UserBase
    status: AppointmentStatus
    class Config:
        from_attributes = True

class DashboardMetrics(BaseModel):
    total_patients: int
    upcoming_appointments: int
    completed_appointments_today: int
    
    class Config:
        from_attributes = True

class UserSettingsBase(BaseModel):
    dark_mode: bool = False
    language: str = 'es'
    notifications_enabled: bool = True

class UserSettings(UserSettingsBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    message: str
    is_read: bool

class Notification(NotificationBase):
    id: int
    created_at: datetime
    type_name: str
    class Config:
        from_attributes = True

class AppointmentUpdate(BaseModel):
    """
    Esquema para ACTUALIZAR una cita.
    Todos los campos son opcionales.
    """
    appointment_date: datetime | None = None
    reason: str | None = None
    doctor_id: int | None = None
    status_id: int | None = None
