from typing import Sequence
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.persona import Persona
from ..views.persona import PersonaCreate, PersonaUpdate
from .errors import PersonaNotFoundError, EmailAlreadyExistsError

from faker import Faker  

fake = Faker('es_ES')  # Inicializar Faker en español

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

import random
from datetime import date

def poblar_base_datos(db: Session, cantidad: int):
    """Genera e inserta un bloque de personas con datos aleatorios."""
    dominios_reales = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com"]
    
    for _ in range(cantidad):
        primer_nombre = fake.first_name()
        segundo_nombre = fake.first_name() if random.random() > 0.5 else None
        primer_apellido = fake.last_name()
        segundo_apellido = fake.last_name()
        
        nombre_base = f"{primer_nombre.lower()}.{primer_apellido.lower()}"
        dominio = random.choice(dominios_reales)
        email = f"{nombre_base}{random.randint(10, 99)}@{dominio}"
        
        phone = fake.phone_number()
        birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90)
        is_active = fake.boolean(chance_of_getting_true=70)
        notes = fake.sentence(nb_words=6) if random.random() > 0.3 else None
        
        # Crear la instancia del modelo SQLAlchemy
        nueva_persona = Persona(
            first_name=primer_nombre,
            last_name=f"{primer_apellido} {segundo_apellido}".strip(),
            email=email,
            phone=phone,
            birth_date=birth_date,
            is_active=is_active,
            notes=notes
        )
        db.add(nueva_persona)
    
    # Confirmar la transacción en la base de datos
    db.commit()

def reiniciar_tabla(db: Session) -> int:
    """Elimina todos los registros de la tabla personas y retorna el conteo de borrados."""
    # Contar registros actuales antes de la eliminación
    contador_eliminados = db.query(Persona).count()
    
    # Ejecutar el borrado masivo de la tabla
    db.query(Persona).delete()
    db.commit()
    
    return contador_eliminados

from sqlalchemy import func

def contar_por_dominio(db: Session) -> dict:
    """Extrae el dominio de los correos, los agrupa y retorna su conteo."""
    # Equivalente a: SELECT SUBSTRING_INDEX(email, '@', -1) as dominio, COUNT(*) ... GROUP BY dominio
    consulta = (
        db.query(
            func.substring_index(Persona.email, "@", -1).label("dominio"),
            func.count(Persona.id).label("conteo")
        )
        .group_by("dominio")
        .all()
    )
    
    # Transformar el resultado de la consulta en el formato JSON requerido
    return {dominio: conteo for dominio, conteo in consulta}

