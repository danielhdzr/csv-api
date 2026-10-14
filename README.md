# Sales CSV Server

**English** | [Español](README.es.md)

A FastAPI service that receives a sales CSV file, validates it and stores its rows in PostgreSQL.
If the file has any error, nothing is saved: the response lists every error with its line and
column.

> The API, the CSV columns and the error messages are in Spanish (the domain language of the
> project); this README explains them in English.

## Run it

Requires Docker.

```bash
docker compose up -d --build
```

- API: http://localhost:8000 (redirects to the interactive docs at `/docs`, where you can upload a
  CSV with "Try it out")
- PostgreSQL: `localhost:5433`, user `postgres`, password `postgres`, database `ventas`

Credentials and ports can be changed by copying `.env.example` to `.env`; without that file the
defaults above are used.

The `ventas` table is created automatically when the API starts. Data persists in the `pgdata`
volume; `docker compose down -v` deletes it.

## Upload a file

```bash
curl -F "archivo=@ventas_muestra.csv" http://localhost:8000/upload
```

| Status | When                                                      |
|--------|-----------------------------------------------------------|
| 200    | Valid file; returns `filas_guardadas` (rows saved)        |
| 422    | Invalid file; returns the errors, nothing is saved        |
| 413    | The file is larger than 5 MB                              |
| 503    | The database write failed; nothing is saved               |

Example 422 response (at most 50 errors are listed; `total_errores` holds the full count):

```json
{
  "detalle": "El CSV no es válido; no se guardó ninguna fila.",
  "total_errores": 10,
  "errores": [
    {"fila": 3, "columna": "cantidad", "mensaje": "debe ser mayor que 0 (recibido: 0)"}
  ]
}
```

`fila` is the line number in the file (the header is line 1). It is `null` for errors that
affect the whole file, such as a wrong encoding.

Uploading an `id` that already exists updates that row, so loading the same file twice does not
duplicate data.

## CSV format

UTF-8 (with or without BOM), comma-separated, with a header row. Columns may come in any order,
but must be exactly these:

| Column            | Meaning    | Rule                                                      |
|-------------------|------------|-----------------------------------------------------------|
| `id`              | Sale ID    | Integer greater than 0, unique within the file            |
| `cliente`         | Customer   | Non-empty text                                            |
| `ciudad`          | City       | Non-empty text                                            |
| `producto`        | Product    | Non-empty text                                            |
| `cantidad`        | Quantity   | Integer greater than 0                                    |
| `precio_unitario` | Unit price | Number greater than 0, at most 2 decimals, dot separator  |
| `fecha`           | Date       | `YYYY-MM-DD`                                              |

Whitespace around values and blank lines are ignored.

Sample files included:

- `ventas_muestra.csv`: 100 valid rows.
- `ventas_defectuoso.csv`: a different error on each row; the whole file is rejected.
- `ventas_sin_columnas.csv`: wrong header.

## View the data

```bash
docker compose exec db psql -U postgres -d ventas -c "SELECT * FROM ventas LIMIT 10;"
```

Or use a GUI client (Postico, DBeaver, pgAdmin) with the connection details above. Mind the
port: it is `5433`, not the default `5432`.

## Tests

The API tests need the database running (`docker compose up -d db`) and use a separate
`ventas_test` database, created automatically, so they never touch the `ventas` data. If
Postgres is not available those tests are skipped and the validation tests still run.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Tests also run on GitHub Actions on every push (`.github/workflows/tests.yml`).

To point at another server: `TEST_PG_SERVER=postgresql://user:password@host:port .venv/bin/pytest`.

## Project structure

- `main.py`: the API (`POST /upload`), table creation and saving in a single transaction.
- `validation.py`: CSV parsing and validation.
- `tests/`: validation and API tests.
