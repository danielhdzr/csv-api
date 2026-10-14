import pytest

from validation import validar_csv

ENCABEZADO = "id,cliente,ciudad,producto,cantidad,precio_unitario,fecha\n"


def csv_con(*lineas):
    return (ENCABEZADO + "".join(l + "\n" for l in lineas)).encode()


def un_error(contenido):
    filas, errores = validar_csv(contenido)
    assert len(errores) == 1, errores
    return errores[0]


def test_archivo_de_muestra_es_valido(leer):
    filas, errores = validar_csv(leer("ventas_muestra.csv"))
    assert errores == []
    assert len(filas) == 100
    assert [f["id"] for f in filas] == list(range(1, 101))


def test_archivo_defectuoso_reporta_cada_error(leer):
    _, errores = validar_csv(leer("ventas_defectuoso.csv"))
    assert [(e["fila"], e["columna"]) for e in errores] == [
        (3, "cantidad"),
        (4, "cliente"),
        (5, "cantidad"),
        (6, "precio_unitario"),
        (7, "precio_unitario"),
        (8, "fecha"),
        (9, "fecha"),
        (10, "id"),
        (11, None),
        (12, "id"),
    ]


def test_archivo_con_columnas_equivocadas(leer):
    _, errores = validar_csv(leer("ventas_sin_columnas.csv"))
    mensajes = [e["mensaje"] for e in errores]
    assert "Faltan columnas: precio_unitario" in mensajes
    assert "Columnas no reconocidas: precio, vendedor" in mensajes


def test_convierte_tipos_y_quita_espacios():
    filas, errores = validar_csv(csv_con(" 7 , Ana ,CDMX,Mouse, 2 ,10.5, 2026-01-31 "))
    assert errores == []
    fila = filas[0]
    assert fila["id"] == 7 and fila["cantidad"] == 2
    assert fila["cliente"] == "Ana"
    assert str(fila["precio_unitario"]) == "10.5"
    assert fila["fecha"].isoformat() == "2026-01-31"


def test_acepta_columnas_en_otro_orden_bom_comillas_y_lineas_en_blanco():
    contenido = (
        "﻿fecha,precio_unitario,cantidad,producto,ciudad,cliente,id\r\n"
        '2026-01-01,5.00,1,"Cable, USB",CDMX,Ana,1\r\n'
        "\r\n"
    ).encode()
    filas, errores = validar_csv(contenido)
    assert errores == []
    assert filas[0]["producto"] == "Cable, USB"


@pytest.mark.parametrize("contenido, mensaje", [
    (b"", "El archivo está vacío"),
    (b"  \n\n", "El archivo está vacío"),
    ("ñ".encode("latin-1"), "El archivo no está codificado en UTF-8"),
    (ENCABEZADO.encode(), "El archivo tiene encabezado pero ninguna fila de datos"),
])
def test_archivos_sin_datos_utiles(contenido, mensaje):
    assert un_error(contenido)["mensaje"] == mensaje


def test_columnas_repetidas():
    _, errores = validar_csv(b"id,id,cliente,ciudad,producto,cantidad,precio_unitario,fecha\n")
    assert "Columnas repetidas: id" in [e["mensaje"] for e in errores]


def test_caracter_nulo_se_rechaza():
    assert "caracteres nulos" in un_error(csv_con("1,A\x00na,CDMX,Mouse,1,10,2026-01-01"))["mensaje"]


def test_campo_gigante_no_rompe_el_servidor():
    error = un_error(csv_con(f"1,{'x' * 200_000},CDMX,Mouse,1,10,2026-01-01"))
    assert error["mensaje"].startswith("El CSV está mal formado")


@pytest.mark.parametrize("valor", ["1_0", "1e3", "+5", "1.0", "١٢", "2147483648", "0", "-1"])
def test_enteros_invalidos(valor):
    assert un_error(csv_con(f"{valor},Ana,CDMX,Mouse,1,10,2026-01-01"))["columna"] == "id"


@pytest.mark.parametrize("valor", ["1e3", "NaN", "Infinity", "1_000", "10.", ".5", "0", "-1", "1.234",
                                   "10000000000.00"])
def test_precios_invalidos(valor):
    assert un_error(csv_con(f"1,Ana,CDMX,Mouse,1,{valor},2026-01-01"))["columna"] == "precio_unitario"


@pytest.mark.parametrize("valor", ["10", "10.5", "10.50", "9999999999.99"])
def test_precios_validos(valor):
    filas, errores = validar_csv(csv_con(f"1,Ana,CDMX,Mouse,1,{valor},2026-01-01"))
    assert errores == []


@pytest.mark.parametrize("valor", ["20260101", "2026-1-1", "2026-02-30", "01/02/2026", "2026-W01-1", ""])
def test_fechas_invalidas(valor):
    assert un_error(csv_con(f"1,Ana,CDMX,Mouse,1,10,{valor}"))["columna"] == "fecha"


def test_reporta_todos_los_errores_de_una_fila():
    _, errores = validar_csv(csv_con("x,,,,0,-1,ayer"))
    assert {e["columna"] for e in errores} == {
        "id", "cliente", "ciudad", "producto", "cantidad", "precio_unitario", "fecha"}
