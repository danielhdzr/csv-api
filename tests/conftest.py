import os
from pathlib import Path

import psycopg
import pytest

# Los tests de la API usan una base aparte para no tocar los datos de "ventas".
# Debe definirse antes de importar main, que lee DATABASE_URL al cargarse.
SERVIDOR = os.getenv("TEST_PG_SERVER", "postgresql://postgres:postgres@localhost:5433")
os.environ["DATABASE_URL"] = f"{SERVIDOR}/ventas_test"

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def leer():
    return lambda nombre: (RAIZ / nombre).read_bytes()


@pytest.fixture(scope="session")
def base_de_pruebas():
    try:
        with psycopg.connect(f"{SERVIDOR}/postgres", autocommit=True, connect_timeout=3) as conn:
            if not conn.execute("SELECT 1 FROM pg_database WHERE datname = 'ventas_test'").fetchone():
                conn.execute("CREATE DATABASE ventas_test")
    except psycopg.OperationalError:
        pytest.skip(f"Postgres no disponible en {SERVIDOR}; levántalo con `docker compose up -d db`")
    return os.environ["DATABASE_URL"]


@pytest.fixture
def cliente(base_de_pruebas):
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as c:  # ejecuta el lifespan, que crea la tabla
        with psycopg.connect(base_de_pruebas) as conn:
            conn.execute("TRUNCATE ventas")
        yield c


@pytest.fixture
def contar_filas(base_de_pruebas):
    def contar():
        with psycopg.connect(base_de_pruebas) as conn:
            return conn.execute("SELECT count(*) FROM ventas").fetchone()[0]
    return contar
