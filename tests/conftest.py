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

import pytest


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
