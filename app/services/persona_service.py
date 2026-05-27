from typing import Sequence
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, text

from ..models.persona import Persona
from ..views.persona import PersonaCreate, PersonaUpdate
from .errors import PersonaNotFoundError, EmailAlreadyExistsError


def create_persona(db: Session, payload: PersonaCreate) -> Persona:
    """Create a Persona ensuring unique email."""
    # Optimistic check; DB unique constraint is the final guard
    if db.query(Persona).filter(Persona.email == payload.email).first():
        raise EmailAlreadyExistsError()
    obj = Persona(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        birth_date=payload.birth_date,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Catch race conditions on unique email
        raise EmailAlreadyExistsError() from e
    db.refresh(obj)
    return obj


def list_personas(db: Session, skip: int = 0, limit: int = 100) -> Sequence[Persona]:
    """Return paginated list of Personas."""
    return db.query(Persona).offset(skip).limit(limit).all()


def get_persona(db: Session, persona_id: int) -> Persona:
    """Return Persona by ID or raise if not found."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()
    return obj


def update_persona(db: Session, persona_id: int, payload: PersonaUpdate) -> Persona:
    """Update Persona partially, enforcing unique email."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != obj.email:
        if db.query(Persona).filter(Persona.email == data["email"], Persona.id != persona_id).first():
            raise EmailAlreadyExistsError()

    for field, value in data.items():
        setattr(obj, field, value)

    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise EmailAlreadyExistsError() from e
    db.refresh(obj)
    return obj


def delete_persona(db: Session, persona_id: int) -> None:
    """Delete Persona by ID or raise if not found."""
    obj = db.query(Persona).filter(Persona.id == persona_id).first()
    if not obj:
        raise PersonaNotFoundError()
    db.delete(obj)
    db.commit()


def estadisticas_edad(db: Session):
    result = db.execute(
        text("""
            SELECT 
                ROUND(AVG(TIMESTAMPDIFF(YEAR, birth_date, CURDATE()))) AS promedio,
                MIN(TIMESTAMPDIFF(YEAR, birth_date, CURDATE())) AS minima,
                MAX(TIMESTAMPDIFF(YEAR, birth_date, CURDATE())) AS maxima
            FROM personas
        """)
    ).fetchone()
    
    if result is None or result[0] is None:
        return {"edad_promedio": None, "edad_minima": None, "edad_maxima": None}
    
    return {
        "edad_promedio": result[0],
        "edad_minima": result[1],
        "edad_maxima": result[2]
    }


def buscar_personas(db: Session, termino: str):
    like = f"%{termino}%"

    return db.query(Persona).filter(
        (Persona.first_name.ilike(like)) |
        (Persona.last_name.ilike(like)) |
        (Persona.email.ilike(like))
    ).all()


def reporte_activos(db: Session):
    results = db.query(
        Persona.id,
        Persona.email,
        Persona.phone,
        Persona.is_active
    ).filter(Persona.is_active == True).all()

    return [
        {
            "id": r.id,
            "email": r.email,
            "phone": r.phone,
            "is_active": r.is_active
        }
        for r in results
    ]