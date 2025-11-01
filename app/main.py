# --- app/main.py ---

from fastapi import FastAPI
# 1. Importa TODOS tus routers (con importación relativa)
from .routers import auth, users, patients, appointments, dashboard, settings, notifications

# -----------------
# Creación de la App
# -----------------
app = FastAPI(
    title="Clinic API",
    description="API para la gestión de la Clínica - Proyecto 2P",
    version="0.1.0",
    contact={
        "name": "Tu Nombre Aquí",
        "email": "tu@email.com",
    },
)

# -----------------
# Inclusión de Routers
# -----------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(notifications.router)  # <-- ¡AÑADIDO!

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
