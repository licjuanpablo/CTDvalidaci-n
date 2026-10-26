// Arma el pedido de EXTRACCIÓN para el sub-workflow "Gemini con rotación de claves (Hark)" (kYDhcme8j6T8BZ7O).
// Principio: Gemini solo extrae y sugiere; las reglas determinísticas del nodo siguiente deciden.
// Si el formulario trae sin_ia=1 el sub-workflow no llama a Gemini (gemini.skip) y decide solo con reglas.
const docs = $('Obtener todos los textos').first().json.data || [];
let sinIA = false;
try { sinIA = !!$('Split archivos').first().json.sinIA; } catch (e) {}

// Redacción mínima de datos personales antes de enviar a Gemini (firmas digitales, matrículas, mails, teléfonos)
const redactar = t => (t || '')
  .replace(/(Firmado digitalmente por|Digitally signed by)[^\n]*/gi, '$1 [REDACTADO]')
  .replace(/\b(M\.?\s?N\.?|M\.?\s?P\.?)\s*\d[\d\.]*/g, '[MATRÍCULA]')
  .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[MAIL]')
  .replace(/\(?\+?\d{2,4}\)?[\s-]?\d{3,4}[\s-]\d{4}\b/g, '[TEL]');

const corpus = docs.map((d, i) => `### DOCUMENTO ${i + 1} — archivo: "${d.fileName}"\n${redactar(d.text).slice(0, 20000)}`).join('\n\n');

const esquema = `{
 "documentos": [{"archivo": "", "tipo_canonico": "nota|formulario|tabla_modificaciones|ddjj_cambios|ddjj_no_impactada|certificado|prospecto|info_paciente|rotulo|referencia_ema|referencia_fda|referencia_otra_agencia|resumen_clinico|soporte_calidad|publicacion|otro",
   "rol": "aprobado|control_cambios|proyecto|no_aplica", "evidencia_rol": ["sello_IF|globos_comentario|encabezado_control_cambios|fechas_duplicadas|nombre_archivo|ninguna"],
   "idioma_predominante": "es|en|otro", "producto_mencionado": ""}],
 "certificado": {"n_certificado": "", "titular": "", "nombre_comercial": "", "ifa": "", "concentracion": "", "forma_farmaceutica": "", "vida_util": "", "conservacion": "", "elaborador": ""},
 "nota": {"concepto_codigo": "", "motivo_tramite": "", "nombre_comercial": "", "ifa": "", "concentracion": "", "forma_farmaceutica": "", "n_certificado": "", "titular": "",
   "textos_afectados": {"prospecto": null, "info_paciente": null, "rotulos": null}},
 "tabla_modificaciones": {"formato": "F1_texto_completo|F2_ficha_documento|F3_resumen_seccion|F4_ddjj_pagina|F5_narrativa|F6_externa|F7_legacy|ninguna", "ubicacion_archivo": "",
   "filas": [{"documento": "prospecto|info_paciente|rotulo|ficha", "seccion_original": "", "seccion_canonica": "INDICACIONES|POSOLOGIA|CONTRAINDICACIONES|ADVERTENCIAS|INTERACCIONES|POBLACIONES|RAM|SOBREDOSIS|PROPIEDADES|ESTUDIOS|COMPOSICION|CONSERVACION|PRESENTACION|ELABORADOR|ESPECIFICACIONES|ADMINISTRATIVO|OTRA",
     "estado": "con_modificacion|sin_modificacion", "resumen": "", "remite_a_disposicion_aprobada": false, "es_dato_de_calidad": false}],
   "declara_nueva_indicacion": false},
 "sugerencia": {"asignar_a": "Calidad|Clínica|Ambas", "fundamento": "", "objeciones_posibles": [""], "observaciones_posibles": [""]}
}`;

const prompt = `Sos un asistente de extracción de datos para la validación FORMAL (no de fondo) de trámites de variación post-registro de productos biológicos ante ANMAT (concepto 2302: rótulos, prospectos e información para el paciente).
Recibís el texto de todos los archivos de un expediente. NO decidas el dictamen: solo extraé datos literales y, al final, dejá una sugerencia no vinculante.

Instrucciones:
1. Clasificá cada documento por su CONTENIDO, no por el nombre del archivo. Rol: "aprobado" si lleva sello IF-AAAA-NNNNNNNN-APN-DECBR#ANMAT; "control_cambios" si tiene globos "Comentado [..]"/"Commented [..]", encabezado "CONTROL DE CAMBIOS" o fechas de revisión duplicadas/fusionadas; "proyecto" si es el texto limpio propuesto.
2. Certificado REM: copiá literalmente nombre comercial, IFA, concentración, forma farmacéutica, titular (razón social) y N° de certificado.
3. Nota de presentación: copiá los mismos datos tal como figuran en la nota, el motivo y qué textos dice presentar.
4. Tabla de modificaciones (puede estar en el formulario 1.2, en una declaración jurada de "únicos cambios" o como ficha): una fila por sección declarada como modificada, con el documento al que pertenece y la sección normalizada a la lista canónica (conservá el rótulo original). Marcá estado "sin_modificacion" cuando la tabla diga SIN MODIFICACIÓN, N/A o "no hay modificaciones". Marcá es_dato_de_calidad=true si la fila cambia fórmula/excipientes (cantidades), elaborador, vida útil, conservación, especificaciones o envase. Marcá remite_a_disposicion_aprobada=true si la fila dice que el cambio ya fue aprobado por una disposición previa.
5. Idioma: indicá el idioma predominante de cada documento.
6. No inventes ni infieras: si un dato no está, dejalo vacío. No incluyas nombres de personas.
Respondé SOLO con un JSON válido con este esquema:
${esquema}

EXPEDIENTE:
${corpus}`;

const body = {
  contents: [{ role: 'user', parts: [{ text: prompt }] }],
  generationConfig: { responseMimeType: 'application/json', temperature: 0 }
};
return [{ json: { body, gemini: { check: 'json', prefer_key: 'C', purpose: 'ctd-validador-clinico', skip: sinIA } } }];
