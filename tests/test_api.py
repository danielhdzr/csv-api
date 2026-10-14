def subir(cliente, nombre, contenido):
    return cliente.post("/upload", files={"archivo": (nombre, contenido, "text/csv")})


def test_sube_el_archivo_de_muestra(cliente, leer, contar_filas):
    r = subir(cliente, "ventas_muestra.csv", leer("ventas_muestra.csv"))
    assert r.status_code == 200
    assert r.json() == {"archivo": "ventas_muestra.csv", "filas_guardadas": 100}
    assert contar_filas() == 100


def test_subir_dos_veces_no_duplica(cliente, leer, contar_filas):
    for _ in range(2):
        assert subir(cliente, "ventas_muestra.csv", leer("ventas_muestra.csv")).status_code == 200
    assert contar_filas() == 100


def test_archivo_defectuoso_no_guarda_nada(cliente, leer, contar_filas):
    r = subir(cliente, "ventas_defectuoso.csv", leer("ventas_defectuoso.csv"))
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["total_errores"] == 10
    assert cuerpo["errores"][0] == {
        "fila": 3, "columna": "cantidad", "mensaje": "debe ser mayor que 0 (recibido: 0)"}
    assert contar_filas() == 0


def test_limita_los_errores_mostrados(cliente):
    contenido = b"id,cliente,ciudad,producto,cantidad,precio_unitario,fecha\n" + b"x,a,b,c,1,1,2026-01-01\n" * 80
    cuerpo = subir(cliente, "malo.csv", contenido).json()
    assert cuerpo["total_errores"] == 80
    assert len(cuerpo["errores"]) == 50


def test_rechaza_archivos_de_mas_de_5_mb(cliente, contar_filas):
    r = subir(cliente, "grande.csv", b"x" * (5 * 1024 * 1024 + 1))
    assert r.status_code == 413
    assert contar_filas() == 0


def test_falta_el_archivo(cliente):
    assert cliente.post("/upload").status_code == 422


def test_la_raiz_lleva_a_la_documentacion(cliente):
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/docs"
