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
# 2. Esquema del Dashboard (¡MEJORADO!)
# -----------------

class DashboardMetrics(BaseModel):
    """Esquema híbrido para Médico y Admin."""
    # Comunes
    total_patients: int
    
    # Específicos Médico
    upcoming_appointments: int | None = None
    completed_appointments_today: int | None = None
    
    # Específicos Admin (Nuevos)
    total_appointments_today: int | None = None
    active_doctors: int | None = None
    total_users: int | None = None
    
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
    birth_date: date | None = None 

# --- ¡NUEVO! Esquema para que el Admin edite usuarios ---
class UserAdminUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    is_active: bool | None = None
    # Nota: No dejamos cambiar el password aquí por seguridad,
    # eso se hace en otro endpoint o reset.

class RoleUpdate(BaseModel):
    role_id: int

class UserStatusUpdate(BaseModel):
    is_active: bool

class PatientBase(BaseModel):
    full_name: str
    gender: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None

class PatientCreate(PatientBase):
    pass

class PatientProfileUpdate(BaseModel):
    phone: str | None = None
    allergies: str | None = None
    current_medications: str | None = None
    chronic_conditions: str | None = None
    blood_type: str | None = None
    height_cm: int | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    marital_status: str | None = None

class PatientAdminUpdate(PatientProfileUpdate):
    full_name: str | None = None
    email: EmailStr | None = None
    gender: str | None = None
    birth_date: date | None = None 

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

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class Message(BaseModel):
    detail: str

class DoctorAvailabilityBase(BaseModel):
    day_of_week: int 
    start_time: time 
    end_time: time 

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
    time: str 
    is_available: bool

# -----------------
# 5. Esquemas Simples y Públicos
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

class UserPublic(UserBase):
    id: int
    class Config:
        from_attributes = True

# -----------------
# 6. Esquemas Completos
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
    # ¡NUEVO CAMPO!
    profile_picture: str | None = None 
    
    patient_profile: PatientSimple | None = None 
    class Config:
        from_attributes = True

class Patient(PatientBase):
    id: int
    addresses: list[Address] = []       
    appointments: list[AppointmentSimple] = [] 
    medical_notes: list[MedicalNote] = []
    vital_signs: list[VitalSign] = []
    files: list[MedicalFile] = []
    temporary_password: str | None = None 
    
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