# Validación formal de trámites CTD — versión CLÍNICA

Esta carpeta va dentro del repositorio `CTDvalidaci-n`, junto a la versión de calidad (v2, DOI 10.5281/zenodo.23633236), que **no se modifica**. Contiene el validador formal (no evalúa el fondo científico) para variaciones post-registro de productos biológicos del concepto 2302: rótulos, prospectos e información para el paciente. Para cada expediente devuelve:

- **Asignar a:** Calidad, Clínica o Ambas.
- **Dictamen formal:** Apto para evaluación u Objetar.
- **Objeciones** y **observaciones**.

Todo el material es **ficticio**: productos, IFA, laboratorios, elaboradores, certificados y textos son inventados. Los patrones (tipos documentales, sello IF del aprobado, control de cambios, formatos de tabla de modificaciones) se calcaron de expedientes reales anonimizados, sin copiar texto real ni nombres de personas.

## Contenido

| Carpeta / archivo | Qué es |
|---|---|
| `workflow/flujo_clinico_mHuLZEH72B2pkMFs_export.json` | Flujo n8n exportado **sin credenciales ni claves**. La llamada a Gemini va a un sub-workflow de rotación de claves que no se incluye: hay que reemplazar el nodo "Gemini Extracción clínica" por el propio, o mandar `sin_ia=1` |
| `workflow/nodos/*.js` | Código de los nodos: `reglas_clinicas.js` (decide), `pedido_gemini_clinico.js` (prompt de extracción con esquema JSON), `split_archivos.js`, `normalizar_texto.js` y `obtener_textos.js` |
| `scripts/generar_casos_clinicos.py` | Generador de expedientes con semilla fija (`--seed 2510`) |
| `casos/` | DEV (21) y TEST (39) en PDF, más `ground_truth.csv`, `manifest.json` (sha256) y `SELLADO.txt` |
| `casos_devx/` | Referencia del DEV ampliado (semilla 7777, 60 casos, solo para desarrollo). Los PDF se regeneran con `--seed 7777 --out casos_devx` |
| `scripts/correr_casos.py` | Manda cada expediente al webhook y guarda la respuesta cruda. Para TEST impide una segunda corrida |
| `scripts/comparar.py` | Métricas con IC95 de Clopper-Pearson: sensibilidad, especificidad, exactitud del dictamen, exactitud de la asignación, motivos y observaciones |
| `scripts/harness.js` | Corre las reglas localmente (Node) sobre textos ya extraídos por n8n |
| `scripts/recuperar_ejecucion.py` | Recupera de n8n la salida de un caso cuya respuesta HTTP se cortó, sin volver a correrlo |
| `corridas/DEV_v1_ia_20261025_163456/` | DEV final, con Gemini |
| `corridas/TEST_final_v1_20261025_1342/` | **TEST, corrido una sola vez** con la versión congelada |
| `corridas/DEV_v0captura_20261025_162533/` | Textos de DEV tal como los extrae n8n, que es la entrada del harness |
| `congelamiento_clinico_v1.json` | Hashes del flujo, de las reglas, de la ground truth y del generador, más los criterios de aceptación fijados antes de TEST |
| `SHA256SUMS.txt` | Huellas de todos los archivos |

## Reproducir

```bash
# 1) misma ground truth (los PDF difieren solo en metadatos de fecha de reportlab)
python3 scripts/generar_casos_clinicos.py --seed 2510 --out /tmp/casos && sha256sum /tmp/casos/ground_truth.csv
#    -> 89898560760e640473a502937d88854b4d228301d5025ffc1a9eff1fc9ed4dfc
# 2) reglas sin servidor, sobre los textos capturados de DEV
node scripts/harness.js corridas/DEV_v0captura_20261025_162533 /tmp/salida && python3 scripts/comparar.py /tmp/salida
# 3) métricas de las corridas guardadas
python3 scripts/comparar.py corridas/TEST_final_v1_20261025_1342
# 4) contra un n8n propio: importar el flujo, ajustar URL en correr_casos.py
python3 scripts/correr_casos.py DEV --etiqueta prueba [--sin-ia]
```

## Reglas (resumen)

**Objeciones:**
- falta el certificado REM;
- incongruencia de nombre comercial, IFA, concentración, forma farmacéutica, titular o N° de certificado respecto del REM (en la nota, el formulario, las DDJJ o los textos propuestos);
- documento propio en idioma no español (las referencias de agencias quedan exentas);
- falta la tabla de modificaciones;
- un texto declarado como modificado no trae la versión con control de cambios **o** el proyecto limpio (el rol se decide por contenido: sello IF, globos o encabezado de control de cambios);
- hay un cambio detectable en los textos (diff por sección) que no figura en la tabla.

**Observaciones:** nota ≠ tabla, nueva indicación sin resumen clínico, rol distinto del que sugiere el nombre del archivo, alcance no verificable, duplicados, declarado pero no encontrado, derivación a Calidad sin soporte de Módulo 3.

**Asignación:** por el tipo de cambio, no por palabras clave.
- Clínica: secciones clínicas, o leyenda de excipientes sin cambio de cantidades.
- Calidad: cantidades de la fórmula, conservación o vida útil, elaborador no aprobado previamente, especificaciones.
- Ambas: los dos tipos a la vez.

## Resultados

| Métrica | DEV (21) | TEST (39, una sola vez) |
|---|---|---|
| Sensibilidad (objetar) | 8/8 (IC95 63–100 %) | 19/19 (IC95 82–100 %) |
| Especificidad | 13/13 (IC95 75–100 %) | 20/20 (IC95 83–100 %) |
| Exactitud del dictamen | 21/21 | 39/39 (IC95 91–100 %) |
| Exactitud de la asignación | 21/21 | 39/39 (IC95 91–100 %) |
| Sugerencia de Gemini (no vinculante) | 18/21 | 28/39 |

**Limitación principal:** el generador y las reglas tienen el mismo autor y los PDF son digitales y limpios. Estos números miden la coherencia interna con formatos sintéticos y **no** el desempeño con expedientes reales. Antes de usarlo hace falta un piloto con expedientes reales etiquetados a ciegas. Otras limitaciones:
- el control de cambios hecho solo con resaltado no se ve en el texto;
- no se cubren las tablas F1 (dos columnas intercaladas) ni F7 (legacy);
- no se consolidan certificados legacy;
- una publicación científica en inglés se objeta, porque la regla es literal.

## Nota sobre el empaquetado en GitHub
Por el límite de 100 archivos por subida web, `casos/` y `corridas/` se publican comprimidos en `casos.zip` y `corridas.zip`. Descomprimir en esta misma carpeta antes de correr los scripts; los hashes de `SHA256SUMS.txt` corresponden a los archivos descomprimidos.
