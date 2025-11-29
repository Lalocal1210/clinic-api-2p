from sqlalchemy import (
    Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, Date, Time, 
    CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

# Importamos la Base declarativa de nuestro archivo database.py
from .database import Base

# --- Modelo de Roles ---
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    users = relationship("User", back_populates="role")

# --- Modelo de Usuarios ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # --- ¡NUEVO CAMPO: FOTO DE PERFIL! ---
    profile_picture = Column(String(255), nullable=True) 
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
    # Relación con Rol
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", back_populates="users")
    
    # Relación uno-a-uno con Paciente
    patient_profile = relationship(
        "Patient", 
        back_populates="user", 
        uselist=False, 
        cascade="all, delete-orphan"
    )

    # Relaciones de Disponibilidad (Para Médicos)
    availabilities = relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan")
    blocked_times = relationship("BlockedTime", back_populates="doctor", cascade="all, delete-orphan")


# --- Modelo de Pacientes ---
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    gender = Column(String(10), CheckConstraint("gender IN ('male','female','other')"))
    birth_date = Column(Date, nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
    # Relación uno-a-uno con Usuario
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    user = relationship("User", back_populates="patient_profile", uselist=False)

    # Relaciones inversas (uno-a-muchos)
    addresses = relationship("Address", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    medical_notes = relationship("MedicalNote", back_populates="patient", cascade="all, delete-orphan")
    vital_signs = relationship("VitalSign", back_populates="patient", cascade="all, delete-orphan")
    files = relationship("MedicalFile", back_populates="patient", cascade="all, delete-orphan")
    
    # Campos de perfil extendido
    allergies = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    chronic_conditions = Column(Text, nullable=True)
    blood_type = Column(String(10), nullable=True)
    height_cm = Column(Integer, nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    marital_status = Column(String(50), nullable=True)

# --- Modelo de Direcciones ---
class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    street = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default='México')
    address_type = Column(String(50), default='home')
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    patient = relationship("Patient", back_populates="addresses")

# --- Modelo de Estados de Cita ---
class AppointmentStatus(Base):
    __tablename__ = "appointment_status"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    appointments = relationship("Appointment", back_populates="status")

# --- Modelo de Citas ---
class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("appointment_status.id"), nullable=False, default=1)
    appointment_date = Column(TIMESTAMP(timezone=True), nullable=False)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True) 
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User", foreign_keys=[doctor_id]) 
    status = relationship("AppointmentStatus", back_populates="appointments")

# --- Modelo de Notas Médicas ---
class MedicalNote(Base):
    __tablename__ = "medical_notes"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    patient = relationship("Patient", back_populates="medical_notes")
    doctor = relationship("User", foreign_keys=[doctor_id])
    appointment = relationship("Appointment")

# --- Modelo de Signos Vitales ---
class VitalSign(Base):
    __tablename__ = "vital_signs"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type_name = Column(String(100), nullable=False)
    value = Column(String(50), nullable=False)
    unit = Column(String(50), nullable=True) 
    measured_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    patient = relationship("Patient", back_populates="vital_signs")
    doctor = relationship("User", foreign_keys=[doctor_id])

# --- Modelo de Archivos Médicos ---
class MedicalFile(Base):
    __tablename__ = "medical_files"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(255), nullable=False) 
    description = Column(String(255), nullable=True)
    uploaded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    patient = relationship("Patient", back_populates="files")
    uploader = relationship("User", foreign_keys=[uploader_id])

# --- Modelo de Tipos de Notificación ---
class NotificationType(Base):
    __tablename__ = "notification_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

# --- Modelo de Notificaciones ---
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type_id = Column(Integer, ForeignKey("notification_types.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    user = relationship("User", foreign_keys=[user_id])
    notification_type = relationship("NotificationType")

# --- Modelo de Configuración de Usuario ---
class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    dark_mode = Column(Boolean, default=False)
    language = Column(String(10), default='es')
    notifications_enabled = Column(Boolean, default=True)
    user = relationship("User")


# --- NUEVOS MODELOS DE DISPONIBILIDAD ---

class DoctorAvailability(Base):
    """
    Define el horario base de un médico.
    Ej: Lunes (day=0) de 09:00 a 17:00
    """
    __tablename__ = "doctor_availability"
    id = Column(Integer, primary_key=True, index=True)
    
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    day_of_week = Column(Integer, nullable=False) # 0=Lunes, 6=Domingo
    start_time = Column(Time, nullable=False)     # Ej. 09:00:00
    end_time = Column(Time, nullable=False)       # Ej. 17:00:00
    
    is_active = Column(Boolean, default=True)

    doctor = relationship("User", back_populates="availabilities")

class BlockedTime(Base):
    """
    Define excepciones de tiempo (vacaciones, días libres).
    """
    __tablename__ = "blocked_time"
    id = Column(Integer, primary_key=True, index=True)
    
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    start_datetime = Column(TIMESTAMP(timezone=True), nullable=False)
    end_datetime = Column(TIMESTAMP(timezone=True), nullable=False)
    reason = Column(String(255), nullable=True) # Ej. "Vacaciones"

    doctor = relationship("User", back_populates="blocked_times")