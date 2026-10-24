# Paquete de validación — Asistente de validación formal CTD (prototipo n8n + Gemini)

Todo el contenido de este paquete es **ficticio**: laboratorios, productos, números de expediente, firmantes y datos analíticos fueron generados por un script. No contiene información de expedientes reales ni datos de la ANMAT.

## Contenido

| Carpeta / archivo | Qué es |
|---|---|
| `casos/DEV/` | 19 expedientes de desarrollo. Se usaron para ajustar el sistema, sin límite de corridas. |
| `casos/TEST/` | 41 expedientes congelados. Se ejecutan **una sola vez** con la versión final; sus resultados son los que se informan. |
| `casos/ground_truth.csv` | Resultado esperado de cada caso (veredicto, faltantes, motivo, expediente, producto, empresa, IFA y tipo real de cada archivo). Fijado antes de ejecutar el sistema. |
| `casos/manifest.json` | Semilla y huella SHA-256 de la referencia. |
| `scripts/generar_casos.py` | Genera el set completo (`python3 generar_casos.py --n 60 --dev 20 --seed 2026`). |
| `scripts/correr_casos.py` | Envía cada expediente al webhook del flujo y guarda la respuesta JSON. Completar `URL` con el webhook propio. |
| `scripts/comparar.py` | Compara las respuestas con `ground_truth.csv` y calcula sensibilidad, especificidad, exactitud y aciertos de extracción. |
| `workflow/flujo_validacion_ctd_v1_original.json` | Flujo n8n antes de los ajustes (línea de base). |
| `workflow/flujo_validacion_ctd_v2.json` | Flujo n8n ajustado con los casos DEV. Credenciales y URLs del servidor removidas. |
| `workflow/reglas_deterministicas_v2.js` | Reglas que deciden el veredicto en la versión 2. Gemini extrae y sugiere; no decide. |
| `corridas/` | Respuestas crudas por caso y reportes de cada corrida (se agregan a medida que se ejecutan). |
| `congelamiento_v2.json` | Versión congelada antes de TEST: ids y huellas de los flujos, modelo, huella de la referencia y criterio de aceptación. |
| `SHA256SUMS.txt` | Huella de cada archivo del paquete. |

## Diseño del set

Cada expediente reproduce la estructura de los documentos usados en el trabajo final: **Nota de presentación**, **Formulario de solicitud de modificación post-registro** y **Documento declarado por el regulado** (validación del método analítico, CTD 3.2.S.4.3).

Escenarios: completos en PDF; completos escaneados (JPG, PNG, TIFF); escaneos con ruido; sin número de expediente; falta la nota, el formulario, el documento declarado o varios; nota, formulario o documento declarado con texto ajeno (poema, canción, receta); un documento reemplazado por otro ajeno; producto o empresa inconsistentes entre documentos; documento en formato no admitido (.docx).

Los archivos tienen nombres neutros (`docNN`) y orden aleatorio; el tipo real figura solo en `ground_truth.csv`.

Criterio: **OBJETAR** si falta un documento obligatorio, hay un formato no admitido, un documento no es regulatorio, una sección clave no tiene datos regulatorios o el producto/empresa no coinciden. **VALIDAR** en los demás casos. Un expediente sin número de expediente se valida con el campo informado como `NO IDENTIFICADO`.

## Protocolo

1. Generar el set con semilla fija y registrar la huella de `ground_truth.csv` antes de cualquier ejecución.
2. Ajustar el sistema solo con DEV.
3. Congelar la versión (flujo, reglas, prompt y modelo) y registrar fecha e identificador.
4. Ejecutar TEST una única vez y reportar todos los casos, incluidos los errores.

## Reproducir

```bash
cd scripts
python3 generar_casos.py --n 60 --dev 20 --seed 2026 --out ../casos_regenerados
sha256sum ../casos/ground_truth.csv   # debe coincidir con manifest.json
# importar workflow/flujo_validacion_ctd_v2.json en n8n, configurar credenciales de Gemini y el webhook
python3 correr_casos.py DEV --etiqueta repro
python3 comparar.py corridas/DEV_repro_<fecha>
```

## Limitaciones

Los casos son sintéticos y no reemplazan una evaluación con expedientes reales ni con evaluadores humanos independientes. El resultado del modelo de lenguaje puede variar entre versiones del modelo; por eso el veredicto final queda en reglas determinísticas.
