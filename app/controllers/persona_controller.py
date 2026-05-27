from typing import List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from ..views.persona import PersonaCreate, PersonaUpdate, PersonaRead, PersonaPoblar
from ..database import get_db
from ..services import persona_service

router = APIRouter(prefix="/personas", tags=["personas"])

# Endpoints (van primero para evitar conflicto con /{persona_id}) ─

@router.post("/poblar", status_code=status.HTTP_201_CREATED)
def poblar_personas(datos_in: PersonaPoblar, db: Session = Depends(get_db)):
    """Endpoint para poblar la base de datos con registros falsos."""
    if datos_in.cantidad <= 0 or datos_in.cantidad > 1000:
        raise HTTPException(status_code=400, detail="La cantidad debe estar entre 1 y 1000.")
    persona_service.poblar_base_datos(db=db, cantidad=datos_in.cantidad)
    return {
        "message": f"{datos_in.cantidad} usuarios creados exitosamente",
        "status": 201
    }

@router.delete("/reset", status_code=status.HTTP_200_OK)
def resetear_base_datos(db: Session = Depends(get_db)):
    """Endpoint para eliminar todos los registros de la tabla personas."""
    contador_eliminados = persona_service.reiniciar_tabla(db=db)
    return {
        "message": "Base de datos limpiada. Se eliminaron todos los registros.",
        "deleted_count": contador_eliminados
    }

@router.get("/estadisticas/dominios", status_code=status.HTTP_200_OK)
def obtener_estadisticas_dominios(db: Session = Depends(get_db)):
    """Endpoint para obtener el conteo de usuarios agrupados por dominio de correo."""
    return persona_service.contar_por_dominio(db=db)

# Código base

@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(persona_in: PersonaCreate, db: Session = Depends(get_db)):
    """Create a new Persona delegating to service layer."""
    return persona_service.create_persona(db, persona_in)

@router.get("", response_model=List[PersonaRead])
def list_personas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List Personas with pagination via service layer."""
    return persona_service.list_personas(db, skip=skip, limit=limit)

@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    """Retrieve a Persona by ID via service layer."""
    return persona_service.get_persona(db, persona_id)

@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: int, persona_in: PersonaUpdate, db: Session = Depends(get_db)):
    """Update an existing Persona (partial) via service layer."""
    return persona_service.update_persona(db, persona_id, persona_in)

@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    """Delete a Persona by ID via service layer."""
    persona_service.delete_persona(db, persona_id)
    return None

