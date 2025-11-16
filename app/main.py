import os
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles 
from .routers import (
    auth, 
    users, 
    patients, 
    appointments, 
    dashboard, 
    settings, 
    notifications, 
    admin,
    availability
) 

os.makedirs("static/uploads", exist_ok=True)

app = FastAPI(
    title="Clinic API",
    description="API para la gestión de la Clínica - Proyecto 2P",
    version="0.1.0",
    contact={
        "name": "Tu Nombre Aquí",
        "email": "tu@email.com",
    },
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(availability.router)

@app.get("/", tags=["Root"])
def read_root():
    return {
        "proyecto": "API de Clínica con FastAPI y PostgreSQL",
        "status": "¡API en funcionamiento!",
        "documentacion": "Visita /docs para ver los endpoints"
    }