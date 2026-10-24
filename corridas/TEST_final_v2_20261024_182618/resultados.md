# Resultados TEST_final_v2_20261024_182618

Casos: 41

| Componente | Sensibilidad (detecta los que deben objetarse) | Especificidad (no objeta los correctos) | Exactitud |
|---|---|---|---|
| Veredicto final (reglas) | 21/21 (84%–100%) | 18/20 (68%–99%) | 39/41 |
| Sugerencia del modelo (Gemini) | 12/21 (34%–78%) | 20/20 (83%–100%) | 32/41 |

IC 95 % exacto de Clopper-Pearson.

| Campo extraído por el modelo | Aciertos |
|---|---|
| expediente | 41/41 |
| producto | 40/41 |
| empresa | 40/41 |
| ifa | 41/41 |

## Errores del veredicto final

- CASO-020 (completo_ruidoso): esperado VALIDAR, sistema OBJETAR. La empresa no coincide entre documentos: Inmunogen Pampa S.A. / INUMOGEN PAMPA S.A..
- CASO-059 (completo_escaneado): esperado VALIDAR, sistema OBJETAR. El producto no coincide entre documentos: RUTUXAN-AR 500 mg / RITUXAN-AR 500 mg.

## Errores de extracción

- CASO-039 empresa: esperado «Biofarma Austral S.A.», modelo «Celltech Litoral S.R.L.»
- CASO-059 producto: esperado «RITUXAN-AR 500 mg», modelo «RITUXAN-AR 500 mg *(Nota: en la Nota de Presentación figura tipografiado como "RUTUXAN-AR", pero prevalece el dato del Formulario de Solicitud y CTD)»