# --- app/schemas.py ---

from pydantic import BaseModel, EmailStr
from datetime import date, datetime

# -----------------
# 1. Esquemas de Catálogos y Autenticación
# (No dependen de otros esquemas)
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
# (No depende de otros esquemas)
# -----------------

class DashboardMetrics(BaseModel):
    """
    Esquema para los datos del dashboard del médico.
    """
    total_patients: int
    upcoming_appointments: int
    completed_appointments_today: int
    
    class Config:
        from_attributes = True

# -----------------
# 3. Esquemas de Direcciones
# (No dependen de otros esquemas)
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
# (Definen la entrada de datos para POST/PUT)
# -----------------

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    password: str 

class RoleUpdate(BaseModel):
    """Esquema para actualizar el rol de un usuario."""
    role_id: int

class PatientBase(BaseModel):
    full_name: str
    gender: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    """Esquema para ACTUALIZAR un Paciente. Todos los campos opcionales."""
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

class AppointmentUpdate(BaseModel):
    """Esquema para ACTUALIZAR una cita. Todos los campos opcionales."""
    appointment_date: datetime | None = None
    reason: str | None = None
    doctor_id: int | None = None
    status_id: int | None = None

class MedicalNoteBase(BaseModel):
    title: str
    content: str
    appointment_id: int | None = None # Opcional

class MedicalNoteCreate(MedicalNoteBase):
    pass

class MedicalNoteUpdate(BaseModel):
    """Esquema para ACTUALIZAR una nota. Todos los campos opcionales."""
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
    """Esquema para ACTUALIZAR un signo vital. Todos los campos opcionales."""
    type_name: str | None = None
    value: str | None = None
    unit: str | None = None
    measured_at: datetime | None = None

class MedicalFileBase(BaseModel):
    """Esquema para leer la descripción de un archivo (la entrada es el archivo en sí)"""
    description: str | None = None

class UserSettingsBase(BaseModel):
    """Esquema base para las configuraciones"""
    dark_mode: bool = False
    language: str = 'es'
    notifications_enabled: bool = True

class NotificationBase(BaseModel):
    message: str
    is_read: bool

# -----------------
# 5. Esquemas Simples
# (Usados para mostrar info anidada DENTRO de otros esquemas)
# -----------------

class PatientSimple(BaseModel):
    """Un perfil simple de paciente para mostrar anidado"""
    id: int
    full_name: str
    class Config:
        from_attributes = True

class AppointmentSimple(BaseModel):
    """Un esquema simple de cita para mostrar anidado"""
    id: int
    appointment_date: datetime
    reason: str | None = None
    class Config:
        from_attributes = True

# -----------------
# 6. Esquemas Completos (para LEER)
# (Estos esquemas dependen de los esquemas anteriores)
# -----------------

class MedicalNote(MedicalNoteBase):
    id: int
    created_at: datetime
    doctor: UserBase # Qué doctor la escribió
    patient_id: int 
    class Config:
        from_attributes = True

class VitalSign(VitalSignBase):
    id: int
    patient_id: int
    doctor: UserBase | None = None # Qué doctor los midió (opcional)
    class Config:
        from_attributes = True

class MedicalFile(MedicalFileBase):
    """Esquema para leer un archivo (devuelve la URL y quién lo subió)"""
    id: int
    file_path: str # La URL para acceder al archivo
    uploaded_at: datetime
    uploader: UserBase # Quién lo subió
    class Config:
        from_attributes = True

class User(UserBase):
    """Esquema 'User' completo para leer (incluye rol y perfil)"""
    id: int
    is_active: bool
    role: Role 
    patient_profile: PatientSimple | None = None # Anidado
    class Config:
        from_attributes = True

class Patient(PatientBase):
    """Esquema 'Patient' completo para leer (incluye todo)"""
    id: int
    addresses: list[Address] = []       
    appointments: list[AppointmentSimple] = [] 
    medical_notes: list[MedicalNote] = []
    vital_signs: list[VitalSign] = []
    files: list[MedicalFile] = []
    class Config:
        from_attributes = True

class Appointment(AppointmentBase):
    """Esquema 'Appointment' completo para leer (incluye paciente, doctor y estado)"""
    id: int
    patient: PatientSimple      # Anidado
    doctor: UserBase            # Anidado (solo datos públicos del user)
    status: AppointmentStatus   # Anidado
    class Config:
        from_attributes = True

class UserSettings(UserSettingsBase):
    """Esquema para leer la configuración"""
    id: int
    user_id: int
    class Config:
        from_attributes = True

class Notification(NotificationBase):
    """Esquema para leer una notificación"""
    id: int
    created_at: datetime
    type_name: str # Aplanado para que sea más fácil de leer
    
    class Config:
        from_attributes = True