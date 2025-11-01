# --- app/routers/patients.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importamos todo lo necesario
from .. import models, schemas
from ..database import SessionLocal
# ¡Importamos nuestros "guardias" de seguridad!
from .users import get_current_medico_or_admin_user, get_current_user

# 1. Creamos el router
router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
    # Protegemos TODOS los endpoints en este archivo con esta dependencia
    # Solo "medico" o "admin" pueden usar los endpoints de /patients
    dependencies=[Depends(get_current_medico_or_admin_user)]
)

# 2. Dependencia para la BBDD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 3. Endpoint para CREAR un Paciente
@router.post("/", response_model=schemas.Patient, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: schemas.PatientCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo paciente en la base de datos.
    Solo accesible para roles 'medico' o 'admin'.
    """
    
    # Verificamos si el email del paciente ya existe (si se proporcionó)
    if patient_in.email:
        db_patient = db.query(models.Patient).filter(models.Patient.email == patient_in.email).first()
        if db_patient:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un paciente con este email ya existe."
            )
    
    # Creamos el objeto del modelo
    new_patient = models.Patient(**patient_in.model_dump())
    
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


# 4. Endpoint para LISTAR todos los Pacientes
@router.get("/", response_model=List[schemas.Patient])
def read_patients(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Obtiene una lista de todos los pacientes.
    Solo accesible para roles 'medico' o 'admin'.
    """
    patients = db.query(models.Patient).offset(skip).limit(limit).all()
    return patients


# 5. Endpoint para OBTENER UN Paciente específico
@router.get("/{patient_id}", response_model=schemas.Patient)
def read_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene la información detallada de un solo paciente por su ID.
    (Incluye direcciones, citas, notas y signos vitales).
    Solo accesible para roles 'medico' o 'admin'.
    """
    
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado."
        )
    return db_patient


# 6. Endpoint para ACTUALIZAR un Paciente específico
@router.put("/{patient_id}", response_model=schemas.Patient)
def update_patient(
    patient_id: int,
    patient_in: schemas.PatientUpdate, # Usamos el schema de actualización
    db: Session = Depends(get_db)
):
    """
    Actualiza la información de un paciente específico por su ID.
    Solo accesible para roles 'medico' o 'admin'.
    """
    
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado."
        )
        
    # Actualiza solo los campos enviados
    update_data = patient_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_patient, key, value)
        
    db.commit()
    db.refresh(db_patient)
    return db_patient


# 7. Endpoint para ELIMINAR un Paciente específico
@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un paciente específico por su ID.
    También elimina en cascada sus direcciones, citas, notas y signos vitales.
    Solo accesible para roles 'medico' o 'admin'.
    """
    
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado."
        )
        
    db.delete(db_patient)
    db.commit()
    
    # HTTP 204 No Content no devuelve cuerpo
    return None

# -----------------
# 8. Endpoints Anidados: NOTAS MÉDICAS
# -----------------

@router.post(
    "/{patient_id}/notes", 
    response_model=schemas.MedicalNote, 
    status_code=status.HTTP_201_CREATED
)
def create_medical_note_for_patient(
    patient_id: int,
    note_in: schemas.MedicalNoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # Re-usamos get_current_user
):
    """
    Crea una nueva nota médica para un paciente específico.
    Solo accesible para 'medico' o 'admin'.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paciente no encontrado."
        )

    new_note = models.MedicalNote(
        **note_in.model_dump(),
        patient_id=patient_id,
        doctor_id=current_user.id 
    )
    
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

@router.get(
    "/{patient_id}/notes", 
    response_model=List[schemas.MedicalNote]
)
def read_medical_notes_for_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las notas médicas de un paciente específico.
    Solo accesible para 'medico' o 'admin'.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paciente no encontrado."
        )
    return db_patient.medical_notes

# -----------------
# 9. Endpoints Anidados: SIGNOS VITALES
# -----------------

@router.post(
    "/{patient_id}/vitals", 
    response_model=schemas.VitalSign, 
    status_code=status.HTTP_201_CREATED
)
def create_vital_sign_for_patient(
    patient_id: int,
    vital_in: schemas.VitalSignCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # Re-usamos get_current_user
):
    """
    Crea un nuevo registro de signo vital para un paciente específico.
    Solo accesible para 'medico' o 'admin'.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paciente no encontrado."
        )

    new_vital = models.VitalSign(
        **vital_in.model_dump(),
        patient_id=patient_id,
        doctor_id=current_user.id
    )
    
    db.add(new_vital)
    db.commit()
    db.refresh(new_vital)
    return new_vital

@router.get(
    "/{patient_id}/vitals", 
    response_model=List[schemas.VitalSign]
)
def read_vital_signs_for_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de signos vitales de un paciente específico.
    Solo accesible para 'medico' o 'admin'.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paciente no encontrado."
        )
    return db_patient.vital_signs 

# 10. Endpoints Anidados: GESTIÓN DE NOTAS
# -----------------

@router.put(
    "/{patient_id}/notes/{note_id}",
    response_model=schemas.MedicalNote
)
def update_medical_note(
    patient_id: int,
    note_id: int,
    note_in: schemas.MedicalNoteUpdate, # Usamos el schema de actualización
    db: Session = Depends(get_db)
):
    """
    Actualiza una nota médica específica de un paciente.
    Solo accesible para 'medico' o 'admin'.
    """
    db_note = db.query(models.MedicalNote).filter(
        models.MedicalNote.id == note_id,
        models.MedicalNote.patient_id == patient_id
    ).first()

    if db_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota médica no encontrada para este paciente."
        )

    update_data = note_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_note, key, value)
        
    db.commit()
    db.refresh(db_note)
    return db_note


@router.delete(
    "/{patient_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_medical_note(
    patient_id: int,
    note_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina una nota médica específica de un paciente.
    Solo accesible para 'medico' o 'admin'.
    """
    db_note = db.query(models.MedicalNote).filter(
        models.MedicalNote.id == note_id,
        models.MedicalNote.patient_id == patient_id
    ).first()

    if db_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota médica no encontrada para este paciente."
        )
        
    db.delete(db_note)
    db.commit()
    return None

# -----------------
# 11. Endpoints Anidados: GESTIÓN DE SIGNOS VITALES
# -----------------

@router.put(
    "/{patient_id}/vitals/{vital_id}",
    response_model=schemas.VitalSign
)
def update_vital_sign(
    patient_id: int,
    vital_id: int,
    vital_in: schemas.VitalSignUpdate, # Usamos el schema de actualización
    db: Session = Depends(get_db)
):
    """
    Actualiza un registro de signo vital específico de un paciente.
    Solo accesible para 'medico' o 'admin'.
    """
    db_vital = db.query(models.VitalSign).filter(
        models.VitalSign.id == vital_id,
        models.VitalSign.patient_id == patient_id
    ).first()

    if db_vital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de signo vital no encontrado para este paciente."
        )

    update_data = vital_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vital, key, value)
        
    db.commit()
    db.refresh(db_vital)
    return db_vital

@router.delete(
    "/{patient_id}/vitals/{vital_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_vital_sign(
    patient_id: int,
    vital_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un registro de signo vital específico de un paciente.
    Solo accesible para 'medico' o 'admin'.
    """
    db_vital = db.query(models.VitalSign).filter(
        models.VitalSign.id == vital_id,
        models.VitalSign.patient_id == patient_id
    ).first()

    if db_vital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de signo vital no encontrado para este paciente."
        )
        
    db.delete(db_vital)
    db.commit()
    return None
    