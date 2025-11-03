# --- app/main.py ---

import os
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles # 1. Importa StaticFiles

# 2. Importa TODOS tus routers
from .routers import (
    auth, 
    users, 
    patients, 
    appointments, 
    dashboard, 
    settings, 
    notifications, 
    admin  # <-- El nuevo router
) 

# 3. Asegúrate de que el directorio de subida exista al arrancar
os.makedirs("static/uploads", exist_ok=True)

# -----------------
# Creación de la App
# -----------------
app = FastAPI(
    title="Clinic API",
    description="API para la gestión de la Clínica - Proyecto ",
    version="0.1.0",
    contact={
        "name": "EDUARDO CALDRON",
        "email": "tu@email.com",
    },
)

# 4. "Monta" el directorio estático
# Esto hace que cualquier archivo en la carpeta 'static'
# sea accesible en la URL '/static'
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------
# Inclusión de Routers
# -----------------
# 5. "Enchufa" TODOS los routers a la app principal.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(admin.router) # <-- Esta es la nueva línea


# -----------------
# Endpoint Raíz
# -----------------
@app.get("/", tags=["Root"])
def read_root():
    """ 
    Endpoint de bienvenida. 
    Verifica que la API esté funcionando.
    """
    return {
        "proyecto": "API de Clínica con FastAPI y PostgreSQL",
        "status": "¡API en funcionamiento!",
        "documentacion": "Visita /docs para ver los endpoints"
    }