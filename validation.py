import csv
import io
import re
from datetime import date
from decimal import Decimal

COLUMNAS = ["id", "cliente", "ciudad", "producto", "cantidad", "precio_unitario", "fecha"]
TEXTO = ("cliente", "ciudad", "producto")
PRECIO_MAX = Decimal("9999999999.99")  # NUMERIC(12,2)
# int(), Decimal() y date.fromisoformat() aceptan formatos de más ("1_000", "1e3", "20260904").
ENTERO_RE = re.compile(r"-?\d+", re.ASCII)
PRECIO_RE = re.compile(r"-?\d+(\.\d+)?", re.ASCII)
FECHA_RE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


def _error(fila, columna, mensaje):
    return {"fila": fila, "columna": columna, "mensaje": mensaje}


def _entero_positivo(valor):
    if not ENTERO_RE.fullmatch(valor):
        return None, f"'{valor}' no es un entero"
    n = int(valor)
    if n <= 0:
        return None, f"debe ser mayor que 0 (recibido: {n})"
    if n > 2_147_483_647:
        return None, "excede el máximo permitido"
    return n, None


def _precio(valor):
    if not PRECIO_RE.fullmatch(valor):
        return None, f"'{valor}' no es un número"
    d = Decimal(valor)
    if d <= 0:
        return None, f"debe ser mayor que 0 (recibido: {valor})"
    if d > PRECIO_MAX:
        return None, "excede el máximo permitido"
    if d.as_tuple().exponent < -2:
        return None, f"admite como máximo 2 decimales (recibido: {valor})"
    return d, None


def _fecha(valor):
    try:
        if not FECHA_RE.fullmatch(valor):
            raise ValueError
        return date.fromisoformat(valor), None
    except ValueError:
        return None, f"'{valor}' no es una fecha válida; el formato es AAAA-MM-DD"


def validar_csv(contenido: bytes):
    """Devuelve (filas, errores). Si hay errores, no se debe guardar nada."""
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [_error(None, None, "El archivo no está codificado en UTF-8")]

    if not texto.strip():
        return [], [_error(None, None, "El archivo está vacío")]

    if "\x00" in texto:
        return [], [_error(None, None, "El archivo contiene caracteres nulos (no es un CSV de texto)")]

    try:
        return _validar_filas(csv.reader(io.StringIO(texto, newline="")))
    except csv.Error as e:  # p. ej. un campo que supera csv.field_size_limit()
        return [], [_error(None, None, f"El CSV está mal formado: {e}")]


def _validar_filas(lector):
    encabezado = [c.strip() for c in next(lector)]

    errores = []
    faltantes = [c for c in COLUMNAS if c not in encabezado]
    sobrantes = [c for c in encabezado if c not in COLUMNAS]
    repetidas = sorted({c for c in encabezado if encabezado.count(c) > 1})
    if faltantes:
        errores.append(_error(1, None, f"Faltan columnas: {', '.join(faltantes)}"))
    if sobrantes:
        errores.append(_error(1, None, f"Columnas no reconocidas: {', '.join(sobrantes)}"))
    if repetidas:
        errores.append(_error(1, None, f"Columnas repetidas: {', '.join(repetidas)}"))
    if errores:
        errores.append(_error(1, None, f"Se esperaba: {', '.join(COLUMNAS)}"))
        return [], errores

    filas = []
    ids_vistos = {}
    for campos in lector:
        if not campos:  # línea en blanco
            continue
        linea = lector.line_num
        if len(campos) != len(encabezado):
            errores.append(_error(linea, None,
                f"Tiene {len(campos)} campos y se esperaban {len(encabezado)}"))
            continue

        registro = dict(zip(encabezado, (c.strip() for c in campos)))
        fila, hubo_error = {}, False

        def anotar(columna, valor, mensaje):
            nonlocal hubo_error
            if mensaje:
                errores.append(_error(linea, columna, mensaje))
                hubo_error = True
            else:
                fila[columna] = valor

        anotar("id", *_entero_positivo(registro["id"]))
        anotar("cantidad", *_entero_positivo(registro["cantidad"]))
        anotar("precio_unitario", *_precio(registro["precio_unitario"]))
        anotar("fecha", *_fecha(registro["fecha"]))
        for col in TEXTO:
            anotar(col, registro[col], None if registro[col] else "no puede estar vacío")

        if "id" in fila:
            if fila["id"] in ids_vistos:
                errores.append(_error(linea, "id",
                    f"id {fila['id']} repetido (ya aparece en la línea {ids_vistos[fila['id']]})"))
                hubo_error = True
            else:
                ids_vistos[fila["id"]] = linea

        if not hubo_error:
            filas.append(fila)

    if not errores and not filas:
        errores.append(_error(None, None, "El archivo tiene encabezado pero ninguna fila de datos"))
    return filas, errores
