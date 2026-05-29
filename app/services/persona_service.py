from typing import Sequence
import random
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, text

from faker import Faker

from ..models.persona import Persona
from ..views.persona import PersonaCreate, PersonaUpdate
from .errors import PersonaNotFoundError, EmailAlreadyExistsError

fake = Faker('es_ES')


def create_persona(db: Session, payload: PersonaCreate) -> Persona:
    """Create a Persona ensuring unique email."""
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


def poblar_base_datos(db: Session, cantidad: int):
    """Genera e inserta un bloque de personas con datos aleatorios."""
    dominios_reales = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com"]

    for _ in range(cantidad):
        primer_nombre = fake.first_name()
        primer_apellido = fake.last_name()
        segundo_apellido = fake.last_name()

        nombre_base = f"{primer_nombre.lower()}.{primer_apellido.lower()}"
        dominio = random.choice(dominios_reales)
        email = f"{nombre_base}{random.randint(10, 99)}@{dominio}"

        nueva_persona = Persona(
            first_name=primer_nombre,
            last_name=f"{primer_apellido} {segundo_apellido}".strip(),
            email=email,
            phone=fake.phone_number(),
            birth_date=fake.date_of_birth(minimum_age=18, maximum_age=90),
            is_active=fake.boolean(chance_of_getting_true=70),
            notes=fake.sentence(nb_words=6) if random.random() > 0.3 else None
        )
        db.add(nueva_persona)

    db.commit()


def reiniciar_tabla(db: Session) -> int:
    """Elimina todos los registros con TRUNCATE y retorna el conteo previo."""
    contador = db.query(Persona).count()
    db.execute(text("TRUNCATE TABLE personas"))
    db.commit()
    return contador


def contar_por_dominio(db: Session) -> dict:
    """Extrae el dominio de los correos, los agrupa y retorna su conteo."""
    consulta = (
        db.query(
            func.substring_index(Persona.email, "@", -1).label("dominio"),
            func.count(Persona.id).label("conteo")
        )
        .group_by("dominio")
        .all()
    )
    return {dominio: conteo for dominio, conteo in consulta}


def estadisticas_edad(db: Session):
    """Retorna la edad promedio, minima y maxima de todas las personas."""
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
    """Busca personas por nombre, apellido o email usando el termino dado."""
    like = f"%{termino}%"
    return db.query(Persona).filter(
        (Persona.first_name.ilike(like)) |
        (Persona.last_name.ilike(like)) |
        (Persona.email.ilike(like))
    ).all()


def reporte_activos(db: Session):
    """Retorna id, email, phone e is_active de los usuarios activos."""
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


# =====================================================================
# SERVICIOS DE BASE DE DATOS PARA EL LABORATORIO (PUNTOS G, H, I)
# =====================================================================
import csv
import io
from sqlalchemy import extract
from app.models.persona import Persona  # El modelo que representa la tabla de MySQL

def obtener_cumpleanios_mes(db: Session, mes: int):
    """Lógica Punto G: Filtra usando la función EXTRACT (que equivale a MONTH() en SQL)."""
    return db.query(Persona).filter(extract('month', Persona.birth_date) == mes).all()

# Operación en lote optimizada con SQLAlchemy
def desactivar_bulk(db: Session, lista_ids: list):
    """Lógica Punto H: Desactiva los usuarios que existan y reporta los que falten."""
    # 1. Consultar cuáles de los IDs enviados sí están en la base de datos
    personas_existentes = db.query(Persona).filter(Persona.id.in_(lista_ids)).all()
    ids_encontrados = [p.id for p in personas_existentes]
    
    # 2. Cambiar la columna is_active a False para los registros encontrados
    for persona in personas_existentes:
        persona.is_active = False
        
    # Guardamos los cambios en MySQL con un solo Commit de manera eficiente
    db.commit()
    
    # 3. Calcular cuáles IDs NO existían usando diferencias de listas
    ids_no_encontrados = list(set(lista_ids) - set(ids_encontrados))
    
    # Retornamos la estructura exacta que pide el PDF
    return {
        "message": "Operación completada.",
        "desactivados": ids_encontrados,
        "no_encontrados": ids_no_encontrados,
        "total_desactivados": len(ids_encontrados)
    }


def generar_csv_personas(db: Session):
    """Lógica Punto I: Construye un archivo plano de texto en memoria con formato CSV."""
    personas = db.query(Persona).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escribimos las cabeceras requeridas en la guía
    writer.writerow(["id", "first_name", "last_name", "email", "phone", "birth_date", "is_active", "notes"])
    
    # Escribimos los datos de cada fila
    for p in personas:
        writer.writerow([
            p.id,
            p.first_name,
            p.last_name,
            p.email,
            p.phone,
            str(p.birth_date),
            p.is_active,
            p.notes
        ])
        
    # Estructura del flujo de texto para Excel    
    output.seek(0)  # Movemos el cursor al inicio para que FastAPI pueda leer el archivo virtual
    return output
    