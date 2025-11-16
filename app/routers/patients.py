# --- app/routers/patients.py ---

import os
import shutil
import uuid
import secrets 
import string  
from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    File, UploadFile, Form
)
from sqlalchemy.orm import Session
from typing import List

# Importamos los schemas actualizados
from .. import models, schemas, security 
from ..database import SessionLocal
# Importamos ambos guardias para manejar permisos mixtos
from .users import get_current_medico_or_admin_user, get_current_user

# 1. Creamos el router (SIN dependencia global)
router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Directorio para archivos
UPLOAD_DIRECTORY = "static/uploads"

# --- Función auxiliar para contraseña temporal ---
def generate_temp_password(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


# ==========================================
# 4. CRUD DE PACIENTES
# ==========================================

@router.post("/", response_model=schemas.Patient, status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(get_current_medico_or_admin_user)])
def create_patient(
    patient_in: schemas.PatientCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo paciente Y su cuenta de usuario automáticamente.
    Genera una contraseña temporal. Solo para Médicos/Admins.
    """
    if not patient_in.email:
        raise HTTPException(status_code=400, detail="El email es obligatorio para crear la cuenta.")

    existing_user = db.query(models.User).filter(models.User.email == patient_in.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con este email.")

    temp_password = generate_temp_password()
    hashed_pwd = security.get_password_hash(temp_password)

    try:
        # 4. Crear el USUARIO
        new_user = models.User(
            full_name=patient_in.full_name,
            email=patient_in.email,
            phone=patient_in.phone,
            password_hash=hashed_pwd,
            role_id=3, # Rol Paciente
            is_active=True
        )
        db.add(new_user)
        db.flush() # Asigna ID sin commit final

        # 5. Crear el PACIENTE vinculado
        new_patient = models.Patient(
            **patient_in.model_dump(),
            user_id=new_user.id
        )
        db.add(new_patient)
        
        db.commit()
        db.refresh(new_patient)

        # 6. Inyectamos la contraseña temporal en la respuesta
        new_patient.temporary_password = temp_password
        
        return new_patient

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear paciente: {str(e)}")


@router.get("/", response_model=List[schemas.Patient],
            dependencies=[Depends(get_current_medico_or_admin_user)])
def read_patients(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20, # Límite por defecto para paginación
    search: str | None = None # ¡Soporte para búsqueda!
):
    """
    Obtiene una lista paginada de todos los pacientes.
    Soporta búsqueda por nombre (?search=juan).
    """
    query = db.query(models.Patient)
    
    if search:
        # Filtra por nombre (insensible a mayúsculas/minúsculas)
        query = query.filter(models.Patient.full_name.ilike(f"%{search}%"))
        
    patients = query.order_by(models.Patient.full_name.asc()).offset(skip).limit(limit).all()
    return patients


@router.get("/{patient_id}", response_model=schemas.Patient)
def read_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    # Permisos mixtos: El dueño O un médico/admin
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene la información detallada de un paciente.
    Acceso: Médico/Admin O el propio Paciente.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")

    # Verificación de Permisos
    is_medico_admin = current_user.role.name in ['medico', 'admin']
    is_owner = current_user.patient_profile and current_user.patient_profile.id == patient_id
    
    if not is_medico_admin and not is_owner:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este perfil.")

    return db_patient


@router.put("/{patient_id}", response_model=schemas.Patient)
def update_patient(
    patient_id: int,
    # El body se valida primero con el schema más grande (Admin)
    patient_in: schemas.PatientAdminUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    """
    Actualiza la información de un paciente.
    - Médicos/Admins: Usan PatientAdminUpdate (pueden cambiar todo).
    - Pacientes: Usan PatientProfileUpdate (campos limitados).
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")

    # Verificación de Permisos
    is_medico_admin = current_user.role.name in ['medico', 'admin']
    is_owner = current_user.patient_profile and current_user.patient_profile.id == patient_id
    
    if not is_medico_admin and not is_owner:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para editar este perfil."
        )

    # --- ¡LÓGICA DE PERMISOS DE CAMPO! ---
    update_data = {}
    if is_medico_admin:
        # El Admin/Médico usa el schema completo
        update_data = patient_in.model_dump(exclude_unset=True)
    else:
        # El Paciente (Owner) usa el schema limitado
        profile_update = schemas.PatientProfileUpdate(**patient_in.model_dump(exclude_unset=True))
        update_data = profile_update.model_dump(exclude_unset=True)
        
    # ------------------------------------
        
    for key, value in update_data.items():
        setattr(db_patient, key, value)
        
    db.commit()
    db.refresh(db_patient)
    return db_patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(get_current_medico_or_admin_user)])
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un paciente y sus datos asociados.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
        
    db.delete(db_patient)
    db.commit()
    return None

# ==========================================
# 5. ENDPOINTS ANIDADOS: NOTAS MÉDICAS
# (Solo Médicos/Admins pueden gestionar notas)
# ==========================================

@router.post("/{patient_id}/notes", response_model=schemas.MedicalNote, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_current_medico_or_admin_user)])
def create_medical_note(patient_id: int, note_in: schemas.MedicalNoteCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")

    new_note = models.MedicalNote(
        **note_in.model_dump(),
        patient_id=patient_id,
        doctor_id=current_user.id 
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

@router.get("/{patient_id}/notes", response_model=List[schemas.MedicalNote],
            dependencies=[Depends(get_current_medico_or_admin_user)])
def read_medical_notes(patient_id: int, db: Session = Depends(get_db)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return db_patient.medical_notes

@router.put("/{patient_id}/notes/{note_id}", response_model=schemas.MedicalNote,
            dependencies=[Depends(get_current_medico_or_admin_user)])
def update_medical_note(patient_id: int, note_id: int, note_in: schemas.MedicalNoteUpdate, db: Session = Depends(get_db)):
    db_note = db.query(models.MedicalNote).filter(models.MedicalNote.id == note_id, models.MedicalNote.patient_id == patient_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    for key, value in note_in.model_dump(exclude_unset=True).items():
        setattr(db_note, key, value)
    db.commit()
    db.refresh(db_note)
    return db_note

@router.delete("/{patient_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(get_current_medico_or_admin_user)])
def delete_medical_note(patient_id: int, note_id: int, db: Session = Depends(get_db)):
    db_note = db.query(models.MedicalNote).filter(models.MedicalNote.id == note_id, models.MedicalNote.patient_id == patient_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    db.delete(db_note)
    db.commit()
    return None


# ==========================================
# 6. ENDPOINTS ANIDADOS: SIGNOS VITALES
# (Solo Médicos/Admins)
# ==========================================

@router.post("/{patient_id}/vitals", response_model=schemas.VitalSign, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_current_medico_or_admin_user)])
def create_vital_sign(patient_id: int, vital_in: schemas.VitalSignCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    new_vital = models.VitalSign(**vital_in.model_dump(), patient_id=patient_id, doctor_id=current_user.id)
    db.add(new_vital)
    db.commit()
    db.refresh(new_vital)
    return new_vital

@router.get("/{patient_id}/vitals", response_model=List[schemas.VitalSign],
            dependencies=[Depends(get_current_medico_or_admin_user)])
def read_vital_signs(patient_id: int, db: Session = Depends(get_db)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return db_patient.vital_signs

@router.put("/{patient_id}/vitals/{vital_id}", response_model=schemas.VitalSign,
            dependencies=[Depends(get_current_medico_or_admin_user)])
def update_vital_sign(patient_id: int, vital_id: int, vital_in: schemas.VitalSignUpdate, db: Session = Depends(get_db)):
    db_vital = db.query(models.VitalSign).filter(models.VitalSign.id == vital_id, models.VitalSign.patient_id == patient_id).first()
    if not db_vital:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    for key, value in vital_in.model_dump(exclude_unset=True).items():
        setattr(db_vital, key, value)
    db.commit()
    db.refresh(db_vital)
    return db_vital

@router.delete("/{patient_id}/vitals/{vital_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(get_current_medico_or_admin_user)])
def delete_vital_sign(patient_id: int, vital_id: int, db: Session = Depends(get_db)):
    db_vital = db.query(models.VitalSign).filter(models.VitalSign.id == vital_id, models.VitalSign.patient_id == patient_id).first()
    if not db_vital:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    db.delete(db_vital)
    db.commit()
    return None


# ==========================================
# 7. ENDPOINTS ANIDADADOS: ARCHIVOS (FOTOS)
# ==========================================

@router.post("/{patient_id}/files", response_model=schemas.MedicalFile, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_current_medico_or_admin_user)])
def upload_file(patient_id: int, description: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"patient_{patient_id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, file_name)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo: {e}")
    finally:
        file.file.close()
        
    file_url_path = f"/static/uploads/{file_name}" 
    
    db_file = models.MedicalFile(patient_id=patient_id, uploader_id=current_user.id, file_path=file_url_path, description=description)
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

@router.get("/{patient_id}/files", response_model=List[schemas.MedicalFile])
def read_files(patient_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")

    # Verificación de permisos (mismo que read_patient)
    is_medico_admin = current_user.role.name in ['medico', 'admin']
    is_owner = current_user.patient_profile and current_user.patient_profile.id == patient_id
    
    if not is_medico_admin and not is_owner:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver estos archivos.")
        
    return db_patient.files