# Resultados DEV_v0_original_20261024_181254

Casos: 19

| Componente | Sensibilidad (detecta los que deben objetarse) | Especificidad (no objeta los correctos) | Exactitud |
|---|---|---|---|
| Veredicto final (reglas) | 9/10 (55%–100%) | 1/9 (0%–48%) | 10/19 |
| Sugerencia del modelo (Gemini) | 2/10 (3%–56%) | 7/9 (40%–97%) | 9/19 |

IC 95 % exacto de Clopper-Pearson.

| Campo extraído por el modelo | Aciertos |
|---|---|
| expediente | 12/19 |
| producto | 14/19 |
| empresa | 15/19 |
| ifa | 14/19 |

## Errores del veredicto final

- CASO-003 (completo_pdf): esperado VALIDAR, sistema OBJETAR. Documentos obligatorios faltantes: Nota de Presentación (Módulo 1.0); Formulario de Solicitud (Módulo 1.2); Declaración Jurada (Documento declarado por el regulado).
- CASO-006 (completo_pdf): esperado VALIDAR, sistema OBJETAR. Documentos obligatorios faltantes: Nota de Presentación (Módulo 1.0); Formulario de Solicitud (Módulo 1.2); Declaración Jurada (Documento declarado por el regulado).
- CASO-010 (completo_pdf): esperado VALIDAR, sistema OBJETAR. Documentos obligatorios faltantes: Nota de Presentación (Módulo 1.0); Formulario de Solicitud (Módulo 1.2); Declaración Jurada (Documento declarado por el regulado).
- CASO-012 (completo_sin_nro_exp): esperado VALIDAR, sistema OBJETAR. Documentos obligatorios faltantes: Nota de Presentación (Módulo 1.0); Formulario de Solicitud (Módulo 1.2); Declaración Jurada (Documento declarado por el regulado).
- CASO-013 (completo_ruidoso): esperado VALIDAR, sistema OBJETAR. Documentos obligatorios faltantes: Nota de Presentación (Módulo 1.0); Formulario de Solicitud (Módulo 1.2); Declaración Jurada (Documento declarado por el regulado).
- CASO-014 (completo_escaneado): esperado VALIDAR, sistema ERROR. 
- CASO-017 (completo_pdf): esperado VALIDAR, sistema OBJETAR. Documentos obligatorios faltantes: Nota de Presentación (Módulo 1.0); Formulario de Solicitud (Módulo 1.2); Declaración Jurada (Documento declarado por el regulado).
- CASO-018 (nota_texto_ajeno): esperado OBJETAR, sistema ERROR. 
- CASO-019 (completo_escaneado): esperado VALIDAR, sistema ERROR. 

## Errores de extracción

- CASO-001 expediente: esperado «1-0047-2002-603572-24-3», modelo «NO IDENTIFICADO»
- CASO-001 producto: esperado «BEVASUR 100 mg/4 mL», modelo «NO IDENTIFICADO»
- CASO-001 ifa: esperado «Bevacizumab», modelo «NO IDENTIFICADO»
- CASO-002 expediente: esperado «1-0047-2002-844092-25-7», modelo «NO IDENTIFICADO»
- CASO-002 producto: esperado «TRASTUFIC 150 mg», modelo «NO IDENTIFICADO»
- CASO-002 ifa: esperado «Trastuzumab», modelo «NO IDENTIFICADO»
- CASO-004 expediente: esperado «1-0047-2002-947240-25-6», modelo «NO IDENTIFICADO»
- CASO-014 expediente: esperado «1-0047-2002-921187-24-5», modelo «»
- CASO-014 producto: esperado «BEVASUR 100 mg/4 mL», modelo «»
- CASO-014 empresa: esperado «Celltech Litoral S.R.L.», modelo «»
- CASO-014 ifa: esperado «Bevacizumab», modelo «»
- CASO-015 expediente: esperado «1-0047-2002-131887-26-6», modelo «NO IDENTIFICADO»
- CASO-018 expediente: esperado «1-0047-2002-940696-26-5», modelo «»
- CASO-018 producto: esperado «FILGRAPAMP 300 mcg», modelo «»
- CASO-018 empresa: esperado «Bioterapias del Plata S.R.L.», modelo «»
- CASO-018 ifa: esperado «Filgrastim», modelo «»
- CASO-019 expediente: esperado «1-0047-2002-947495-24-9», modelo «»
- CASO-019 producto: esperado «BEVASUR 100 mg/4 mL», modelo «»
- CASO-019 empresa: esperado «Proteica Rioplatense S.A.», modelo «»
- CASO-019 ifa: esperado «Bevacizumab», modelo «»
- CASO-033 empresa: esperado «Inmunogen Pampa S.A.», modelo «Biofarma Austral S.A.»