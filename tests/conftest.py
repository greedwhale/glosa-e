"""Lo que vale para todos los tests.

Aquí solo hay una cosa, pero es importante: **los tests no miran la carpeta de
esquemas de quien los ejecuta**.

`Catalogo.por_defecto()` lee la variable de entorno `FACTURAE_ESQUEMAS` o, si
no está, la carpeta `esquemas/` del directorio actual. Eso es lo correcto para
la herramienta y lo peor posible para una prueba: significa que el resultado
del test depende de si el desarrollador se ha bajado los XSD oficiales o no.

Y no es una hipótesis. El día que se instalaron los esquemas de verdad para
probar contra facturas ajenas, doce tests que llevaban meses en verde se
pusieron rojos de golpe. Ninguno era sobre esquemas: eran los de `factura.py`,
que construyen facturas mínimas —lo justo para retorcer una regla de negocio— y
que por eso no cumplen el XSD completo, donde `PartyTaxScheme` exige su
`TaxScheme` dentro y `TaxCategory` su `ID`.

Así que la suite declara su supuesto en voz alta: sin esquemas. Quien quiera
probar la validación de forma monta su propio `Catalogo`, que es justo lo que
hace `test_esquema.py`.

**Y sin anclas, por lo mismo.** Se cerró solo lo de los
esquemas y la misma enfermedad siguió viva al lado. El 16-09-2026, al montar
las pruebas en GitHub, la suite pasó entera aquí y en una copia recién clonada
falló `fe-0001.xml`: aquí decía `CADENA-DESCONOCIDA` porque esta carpeta tiene
`anclas/` instaladas; en la copia limpia, `CADENA-SIN-ANCLAS`. La prueba no
fijaba lo que dice el ejemplo, sino lo que tenía instalado quien la corriera.
Quien quiera anclas construye su `Almacen` con la carpeta, que no mira el
entorno.

Las revocaciones no se aíslan porque no se ha visto que hagan falta: con
`FACTURAE_REVOCACIONES` apuntando a una lista ilegible, la suite sale igual.
"""

import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def esquemas_del_paquete(tmp_path_factory):
    """Los esquemas de verdad, sacados de `web/paquete.zip`.

    Ese zip **sí** se versiona, y lleva los XSD de UBL 2.1 y 2.5, de CII y de
    Facturae. Las pruebas que necesitan un esquema real —y no uno de doce
    líneas— los sacan de ahí y no de `esquemas/`: esa carpeta no se versiona,
    así que en una copia recién clonada y en GitHub no existe, y una prueba que
    dependa de ella se salta justo donde más falta hace. Es lo mismo que hace
    `test_paises.py` con su lista.

    Sesión y no función: son 43 ficheros y se sacan una vez. El `Catalogo` que
    se construya encima sí es de cada prueba, porque compila lo suyo.
    """
    destino = tmp_path_factory.mktemp("esquemas-del-paquete")
    with zipfile.ZipFile(RAIZ / "web" / "paquete.zip") as paquete:
        for nombre in paquete.namelist():
            if nombre.startswith("esquemas/") and nombre.endswith(".xsd"):
                paquete.extract(nombre, destino)
    return destino / "esquemas"


@pytest.fixture(autouse=True)
def sin_esquemas_del_entorno(monkeypatch, tmp_path_factory):
    """Apunta el catálogo de esquemas y las anclas a carpetas que no existen.

    A una que no existe y no a una vacía: así también se comprueba de paso, en
    cada test, que no haber esquemas no rompe nada.

    `monkeypatch` deshace el cambio al terminar cada test, y un test que quiera
    otra cosa —`test_por_defecto_lee_la_variable_de_entorno`— la vuelve a poner
    él mismo y gana, porque se ejecuta después.
    """
    base = tmp_path_factory.getbasetemp()
    monkeypatch.setenv("FACTURAE_ESQUEMAS", str(base / "esquemas-que-no-existen"))
    monkeypatch.setenv("FACTURAE_ANCLAS", str(base / "anclas-que-no-existen"))
    # La de sellos se quita en vez de apuntarla a otro sitio: sin ella, las de
    # sellado se buscan al lado de las de firma —`anclas-que-no-existen-sellos`—,
    # que tampoco existe. Ponerla haría que una prueba que cambia solo
    # `FACTURAE_ANCLAS` dejara de encontrar la hermana que espera.
    monkeypatch.delenv("FACTURAE_ANCLAS_SELLOS", raising=False)
