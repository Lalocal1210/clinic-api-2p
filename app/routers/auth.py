# --- app/routers/auth.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 

# Importamos nuestros módulos (con importaciones relativas)
from .. import models, schemas, security
from ..database import SessionLocal, engine

# 1. Creación de Tablas
models.Base.metadata.create_all(bind=engine)

# 2. Creamos un 'router'
router = APIRouter(
    prefix="/auth",  # Todos los endpoints aquí empezarán con /auth
    tags=["Auth"]    # Los agrupa como "Auth" en los /docs
)

# 3. Dependencia para la Sesión de BBDD
def get_db():
    """
    Función de dependencia que crea y cierra
    una sesión de base de datos por cada request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. El Endpoint de Registro (¡ACTUALIZADO Y CORREGIDO!)
@router.post(
    "/register", 
    response_model=schemas.User, 
    status_code=status.HTTP_201_CREATED
)
def create_user(
    user_in: schemas.UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en la base de datos.
    Si el rol es 'paciente', crea también su perfil de paciente vinculado.
    """
    
    # Hasheamos la contraseña
    hashed_password = security.get_password_hash(user_in.password)
    
    # Creamos el objeto del modelo SQLAlchemy (Tabla 'users')
    db_user = models.User(
        full_name=user_in.full_name,
        email=user_in.email,
        phone=user_in.phone,
        password_hash=hashed_password,
        role_id=3,  # 3 = paciente por defecto
        is_active=True
    )
    
    # Guardamos en la BBDD
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user) # Refresca para obtener el ID creado
        
        # --- ¡LÓGICA DE VINCULACIÓN! ---
        if db_user.role_id == 3:
            new_patient_profile = models.Patient(
                full_name=db_user.full_name,
                email=db_user.email,
                phone=db_user.phone,
                birth_date=user_in.birth_date, # Guardamos la fecha
                user_id=db_user.id  # Vinculamos al usuario
            )
            db.add(new_patient_profile)
            db.commit()
            db.refresh(db_user) # Refresca para cargar la relación
        
        return db_user
    
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e).lower()
        # CORRECCIÓN 1: Detectamos el error tanto en inglés como en español
        if "unique constraint" in error_msg or "llave duplicada" in error_msg or "unicidad" in error_msg:
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado."
            )
        # CORRECCIÓN 2: Arreglado el typo HTTP_500 -> HTTP_500_INTERNAL_SERVER_ERROR
        else:
            print(f"Error desconocido de BBDD: {e}") # Log para debug
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al procesar el registro."
            )

# 5. El Endpoint de Login
@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Endpoint para iniciar sesión.
    Recibe un 'username' y 'password' y devuelve un Token JWT.
    """
    
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}, 
        )

    access_token_data = {"sub": user.email, "role": user.role.name}
    access_token = security.create_access_token(data=access_token_data)

    return {"access_token": access_token, "token_type": "bearer"}