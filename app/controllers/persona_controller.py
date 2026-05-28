from typing import List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..views.persona import PersonaCreate, PersonaUpdate, PersonaRead, PersonaPoblar
from ..database import get_db
from ..services import persona_service

router = APIRouter(prefix="/personas", tags=["personas"])


# =====================================================================
# ENDPOINTS ESPECÍFICOS
# =====================================================================

# =====================================================================
# PUNTO A — CARGA DE DATOS
# =====================================================================

@router.post("/poblar", status_code=status.HTTP_201_CREATED)
def poblar_personas(datos_in: PersonaPoblar, db: Session = Depends(get_db)):
    """Endpoint para poblar la base de datos con registros falsos."""
    if datos_in.cantidad <= 0 or datos_in.cantidad > 1000:
        raise HTTPException(
            status_code=400,
            detail="La cantidad debe estar entre 1 y 1000."
        )

    persona_service.poblar_base_datos(db=db, cantidad=datos_in.cantidad)

    return {
        "message": f"{datos_in.cantidad} usuarios creados exitosamente",
        "status": 201
    }

# =====================================================================
# PUNTO B — BORRADO TOTAL
# =====================================================================

@router.delete("/reset", status_code=status.HTTP_200_OK)
def resetear_base_datos(db: Session = Depends(get_db)):
    """Endpoint para eliminar todos los registros de la tabla personas."""
    contador_eliminados = persona_service.reiniciar_tabla(db=db)

    return {
        "message": "Base de datos limpiada. Se eliminaron todos los registros.",
        "deleted_count": contador_eliminados
    }

# =====================================================================
# PUNTO C — ESTADÍSTICAS POR DOMINIO
# =====================================================================

@router.get("/estadisticas/dominios", status_code=status.HTTP_200_OK)
def obtener_estadisticas_dominios(db: Session = Depends(get_db)):
    """Endpoint para obtener el conteo de usuarios agrupados por dominio de correo."""
    return persona_service.contar_por_dominio(db=db)

# =====================================================================
# PUNTO D — ESTADÍSTICAS DE EDAD
# =====================================================================

@router.get("/estadisticas/edad", summary="Estadísticas de edad de personas")
def get_estadisticas_edad(db: Session = Depends(get_db)):
    return persona_service.estadisticas_edad(db)

# =====================================================================
# PUNTO E — BUSCADOR GENERAL
# =====================================================================

@router.get(
    "/buscar/{termino}",
    response_model=List[PersonaRead],
    summary="Buscar personas por nombre, apellido o email"
)
def buscar_personas(termino: str, db: Session = Depends(get_db)):
    return persona_service.buscar_personas(db, termino)

# =====================================================================
# PUNTO F — REPORTE DE ACTIVOS
# =====================================================================

@router.get("/reporte/activos", summary="Reporte de usuarios activos")
def get_reporte_activos(db: Session = Depends(get_db)):
    return persona_service.reporte_activos(db)


# =====================================================================
# PUNTO G — CUMPLEAÑOS POR MES
# =====================================================================

@router.get(
    "/cumpleanios/mes/{numero_mes}",
    summary="Listar personas que cumplen años en un mes específico"
)
def cumpleanios_mes(numero_mes: str, db: Session = Depends(get_db)):
    """Devuelve la lista filtrada de usuarios que cumplen años en el mes."""

    try:
        mes_int = int(numero_mes)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mes debe ser un entero entre 1 y 12."
        )

    if mes_int < 1 or mes_int > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mes debe ser un entero entre 1 y 12."
        )

    return persona_service.obtener_cumpleanios_mes(db, mes_int)


# =====================================================================
# PUNTO H — BULK DESACTIVAR
# =====================================================================

class BulkDesactivarInput(BaseModel):
    ids: List[int]


@router.patch(
    "/bulk/desactivar",
    summary="Desactivación masiva de usuarios por ID"
)
def desactivar_masivo(
    datos_in: BulkDesactivarInput,
    db: Session = Depends(get_db)
):
    """Desactiva múltiples usuarios en una sola operación."""

    if not datos_in.ids or len(datos_in.ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La lista de IDs no puede estar vacía ni superar los 100 elementos."
        )

    return persona_service.desactivar_bulk(db, datos_in.ids)


# =====================================================================
# PUNTO I — EXPORTAR CSV
# =====================================================================

@router.get(
    "/exportar/csv",
    summary="Exportar tabla de personas a archivo CSV"
)
def exportar_csv(db: Session = Depends(get_db)):
    """Retorna todos los registros de la tabla en formato CSV."""

    buffer_csv = persona_service.generar_csv_personas(db)

    headers = {
        "Content-Disposition": 'attachment; filename="personas.csv"'
    }

    return StreamingResponse(
        buffer_csv,
        media_type="text/csv",
        headers=headers
    )


# =====================================================================
# CRUD BASE
# =====================================================================

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


# =====================================================================
# RUTAS DINÁMICAS 
# =====================================================================

@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    """Retrieve a Persona by ID via service layer."""
    return persona_service.get_persona(db, persona_id)


@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(
    persona_id: int,
    persona_in: PersonaUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing Persona (partial) via service layer."""
    return persona_service.update_persona(db, persona_id, persona_in)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    """Delete a Persona by ID via service layer."""
    persona_service.delete_persona(db, persona_id)
    return None
