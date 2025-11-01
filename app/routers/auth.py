# --- app/routers/auth.py ---

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 

# Importamos nuestros módulos (con importaciones relativas)
from .. import models, schemas, security
from ..database import SessionLocal, engine

# 1. Creación de Tablas
# (SQLAlchemy revisa si las tablas de models.py existen, si no, las crea)
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

# 4. El Endpoint de Registro
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
    - **user_in**: Datos de entrada validados por Pydantic (email, password, etc.).
    - **db**: Sesión de BBDD inyectada por la dependencia `get_db`.
    """
    
    # Hasheamos la contraseña
    hashed_password = security.get_password_hash(user_in.password)
    
    # Creamos el objeto del modelo SQLAlchemy
    db_user = models.User(
        full_name=user_in.full_name,
        email=user_in.email,
        phone=user_in.phone,
        password_hash=hashed_password,
        role_id=3  # Asignamos 'paciente' (ID=3) por defecto
    )
    
    # Guardamos en la BBDD
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user) # Refresca el objeto para obtener el ID creado
        return db_user
    
    except IntegrityError as e:
        # Si el error es por la clave foránea (rol no existe)
        if "foreign key constraint" in str(e).lower():
             db.rollback()
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error: El rol de 'paciente' no está configurado en la BBDD."
            )
        # Si el error es por email duplicado
        elif "unique constraint" in str(e).lower():
             db.rollback()
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado."
            )
        # Otro error de integridad
        else:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error de integridad de la base de datos."
            )

# 5. El Endpoint de Login
@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    # 'OAuth2PasswordRequestForm' es una clase especial de FastAPI
    # que solo espera un 'username' y un 'password'
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Endpoint para iniciar sesión.
    Recibe un 'username' y 'password' y devuelve un Token JWT.
    """
    
    # 1. Buscamos al usuario por su email
    # ¡Importante! 'form_data.username' es el campo que usa
    # OAuth2, pero nosotros lo trataremos como el email.
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    # 2. Si el usuario no existe O la contraseña es incorrecta
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}, # Estándar de autenticación
        )

    # 3. Si todo es correcto, creamos el token
    # El 'sub' (subject) es la identidad del token
    # Es crucial añadir el rol aquí para usarlo en los permisos
    access_token_data = {"sub": user.email, "role": user.role.name}
    access_token = security.create_access_token(data=access_token_data)

    # 4. Devolvemos el token
    return {"access_token": access_token, "token_type": "bearer"}