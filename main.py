import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse

from validation import validar_csv

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ventas")
MAX_BYTES = 5 * 1024 * 1024
MAX_ERRORES_MOSTRADOS = 50

CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY,
    cliente         TEXT NOT NULL,
    ciudad          TEXT NOT NULL,
    producto        TEXT NOT NULL,
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12, 2) NOT NULL CHECK (precio_unitario > 0),
    fecha           DATE NOT NULL
)
"""

# Si el id ya existe se actualiza la fila: subir el mismo archivo dos veces no falla ni duplica.
UPSERT = """
INSERT INTO ventas (id, cliente, ciudad, producto, cantidad, precio_unitario, fecha)
VALUES (%(id)s, %(cliente)s, %(ciudad)s, %(producto)s, %(cantidad)s, %(precio_unitario)s, %(fecha)s)
ON CONFLICT (id) DO UPDATE SET
    cliente = EXCLUDED.cliente, ciudad = EXCLUDED.ciudad, producto = EXCLUDED.producto,
    cantidad = EXCLUDED.cantidad, precio_unitario = EXCLUDED.precio_unitario, fecha = EXCLUDED.fecha
"""


def inicializar_db():
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(CREAR_TABLA)


def guardar_filas(filas):
    # Una sola transacción: o se guardan todas las filas o ninguna.
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT, filas)


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_db()
    yield


app = FastAPI(title="Servidor CSV de ventas", lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def inicio():
    return RedirectResponse("/docs")


@app.post("/upload")
async def subir_csv(archivo: UploadFile = File(...)):
    contenido = await archivo.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, f"El archivo supera el máximo de {MAX_BYTES // (1024 * 1024)} MB")

    filas, errores = validar_csv(contenido)
    if errores:
        return JSONResponse(
            status_code=422,
            content={
                "detalle": "El CSV no es válido; no se guardó ninguna fila.",
                "total_errores": len(errores),
                "errores": errores[:MAX_ERRORES_MOSTRADOS],
            },
        )

    try:
        guardar_filas(filas)
    except psycopg.Error:
        raise HTTPException(503, "No se pudo guardar en la base de datos; no se guardó ninguna fila.")
    return {"archivo": archivo.filename, "filas_guardadas": len(filas)}
