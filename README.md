# Servidor CSV de ventas

API en FastAPI que recibe un archivo CSV de ventas, lo valida y guarda sus filas en PostgreSQL.
Si el archivo tiene cualquier error no se guarda nada: se responde con la lista de errores
indicando línea y columna.

## Levantarlo

Requiere Docker.

```bash
docker compose up -d --build
```

- API: http://localhost:8000 (redirige a la documentación interactiva en `/docs`, desde donde se
  puede subir un CSV con "Try it out")
- PostgreSQL: `localhost:5433`, usuario `postgres`, contraseña `postgres`, base `ventas`

La tabla `ventas` se crea sola al arrancar la API. Los datos persisten en el volumen `pgdata`;
`docker compose down -v` los borra.

## Subir un archivo

```bash
curl -F "archivo=@ventas_muestra.csv" http://localhost:8000/upload
```

| Código | Cuándo                                               |
|--------|------------------------------------------------------|
| 200    | Archivo válido; devuelve `filas_guardadas`           |
| 422    | Archivo inválido; devuelve los errores, no guarda nada |
| 413    | El archivo supera 5 MB                               |
| 503    | No se pudo escribir en la base; no guarda nada       |

Ejemplo de respuesta 422 (se muestran como máximo 50 errores; `total_errores` trae el total):

```json
{
  "detalle": "El CSV no es válido; no se guardó ninguna fila.",
  "total_errores": 10,
  "errores": [
    {"fila": 3, "columna": "cantidad", "mensaje": "debe ser mayor que 0 (recibido: 0)"}
  ]
}
```

`fila` es el número de línea del archivo (el encabezado es la línea 1). Es `null` en los errores
que afectan al archivo completo, como una codificación incorrecta.

Subir de nuevo un `id` que ya existe actualiza esa fila, así que cargar el mismo archivo dos veces
no duplica datos.

## Formato del CSV

UTF-8 (con o sin BOM), separado por comas, con encabezado. Las columnas pueden venir en cualquier
orden, pero deben ser exactamente estas:

| Columna           | Regla                                                        |
|-------------------|--------------------------------------------------------------|
| `id`              | Entero mayor que 0, único dentro del archivo                 |
| `cliente`         | Texto no vacío                                               |
| `ciudad`          | Texto no vacío                                               |
| `producto`        | Texto no vacío                                               |
| `cantidad`        | Entero mayor que 0                                           |
| `precio_unitario` | Número mayor que 0, máximo 2 decimales, punto como separador |
| `fecha`           | `AAAA-MM-DD`                                                 |

Se ignoran los espacios alrededor de cada valor y las líneas en blanco.

Archivos de ejemplo incluidos:

- `ventas_muestra.csv`: 100 filas válidas.
- `ventas_defectuoso.csv`: un error distinto en cada fila; se rechaza completo.
- `ventas_sin_columnas.csv`: encabezado equivocado.

## Ver los datos

```bash
docker compose exec db psql -U postgres -d ventas -c "SELECT * FROM ventas LIMIT 10;"
```

O con un cliente gráfico (Postico, DBeaver, pgAdmin) usando los datos de conexión de arriba.
Ojo con el puerto: es `5433`, no el `5432` por defecto.

## Tests

Los tests de la API necesitan la base levantada (`docker compose up -d db`) y usan una base
aparte, `ventas_test`, que crean solos; no tocan los datos de `ventas`. Si Postgres no está
disponible, esos tests se saltan y los de validación corren igual.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Los tests corren también en GitHub Actions en cada push (`.github/workflows/tests.yml`).

Para apuntar a otro servidor: `TEST_PG_SERVER=postgresql://usuario:clave@host:puerto .venv/bin/pytest`.

## Estructura

- `main.py`: la API (`POST /upload`), creación de la tabla y guardado en una sola transacción.
- `validation.py`: lectura y validación del CSV.
- `tests/`: tests de validación y de la API.
