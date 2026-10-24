const raw = $input.first().json;
const respuesta = (raw.candidates?.[0]?.content?.parts || []).filter(p => !p.thought).map(p => p.text || '').join('');   // Gemini 3: puede venir en varias partes
const agregado = $('Obtener todos los textos').all()[0]?.json || { data: [] };

const expedienteFormItems = $('Split archivos').all();
const expedienteForm = expedienteFormItems.find(it => it.json?.expedienteForm)?.json?.expedienteForm || '';

// Archivos rechazados por formato (no se procesan, cuentan como no presentados)
let archivosRechazados = [];
try { archivosRechazados = $('Code in JavaScript').all().filter(it => it.json.archivoInvalido).map(it => it.json.filename); } catch (e) {}

const ahora = new Date();
const offsetMs = -3 * 60 * 60 * 1000;
const ahora_art = new Date(ahora.getTime() + offsetMs);
const pad = n => n.toString().padStart(2, '0');
const timestamp = `${ahora_art.getUTCFullYear()}${pad(ahora_art.getUTCMonth()+1)}${pad(ahora_art.getUTCDate())}_${pad(ahora_art.getUTCHours())}${pad(ahora_art.getUTCMinutes())}${pad(ahora_art.getUTCSeconds())}`;
const timestampLegible = `${pad(ahora_art.getUTCDate())}/${pad(ahora_art.getUTCMonth()+1)}/${ahora_art.getUTCFullYear()} ${pad(ahora_art.getUTCHours())}:${pad(ahora_art.getUTCMinutes())}:${pad(ahora_art.getUTCSeconds())} (ART UTC-3)`;
const meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];

function normalizar(str) {
  return (str || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^\w\s\.\-]/g, ' ').replace(/\s+/g, ' ');
}

// ── CLASIFICACIÓN POR ENCABEZADO (primeros 600 caracteres) ──
// v2 (2026-10-24): se suman los encabezados de las plantillas del TP ("Nota de presentación",
// "Formulario de solicitud de modificación", "Documento declarado por el regulado"), que no se reconocían.
function identificarTipoDocumento(textoCompleto) {
  const enc = normalizar((textoCompleto || '').substring(0, 600));
  if (enc.includes('nota de presentacion') || enc.includes('motivo del tramite') ||
      enc.includes('direccion de evaluacion y control de biologicos') || enc.includes('se dirige a ud') ||
      enc.includes('solicitar autorizacion')) return 'nota';
  if (enc.includes('formulario de solicitud') || enc.includes('antecedentes y descripcion de los cambios') ||
      enc.includes('autorizado vs propuesto') || enc.includes('ficha de modificaciones') ||
      enc.includes('modificacion de aprobacion anterior')) return 'formulario';
  if (enc.includes('documento declarado por el regulado') || enc.includes('declaracion jurada') ||
      (enc.includes('datos generales') && enc.includes('tipo de tramite'))) return 'declaracion';
  return null;
}

const NOMBRES = {
  nota: 'Nota de Presentación (Módulo 1.0)',
  formulario: 'Formulario de Solicitud (Módulo 1.2)',
  declaracion: 'Documento declarado por el regulado'
};

const docs = (agregado.data || []).map(d => ({ ...d, tipo: identificarTipoDocumento(d.text || '') }));
const porTipo = t => docs.find(d => d.tipo === t);

function campo(texto, etiquetas) {
  // La etiqueta y su valor pueden quedar en la misma línea o en la siguiente según cómo se extraiga el PDF.
  for (const et of etiquetas) {
    const m = (texto || '').match(new RegExp('(?:^|\\n)[ \\t]*' + et + '[ \\t]*:\\s*([^\\n]+)', 'i'));
    if (m) {
      const v = m[1].trim();
      if (v && !/:\s*$/.test(v) && !/^SECCI[ÓO]N\b/i.test(v)) return v;
    }
  }
  return '';
}
function bloque(texto, inicio, fin) {
  const m = (texto || '').match(new RegExp(inicio + '\\s*:?\\s*([\\s\\S]+?)(?:' + fin + '|$)', 'i'));
  return m ? m[1].replace(/\s*\n\s*/g, ' ').trim() : '';
}

// ── EXTRACCIÓN POR DOCUMENTO ──
const nota = porTipo('nota'), form = porTipo('formulario'), decl = porTipo('declaracion');
const datos = {
  nota: nota ? {
    producto: campo(nota.text, ['Nombre Comercial']),
    empresa: campo(nota.text, ['Titular del Registro']),
    contenido: bloque(nota.text, 'MOTIVO DE LA MODIFICACI[ÓO]N SOLICITADA', 'Se adjunta|\\n\\s*N°\\s*RECIBO|Sin otro particular') ||
               bloque(nota.text, 'MOTIVO DEL TR[ÁA]MITE', 'Expediente de referencia|Se adjunta|\\n\\s*N°\\s*RECIBO|\\n\\s*\\n')
  } : null,
  formulario: form ? {
    producto: campo(form.text, ['Nombre Comercial']),
    empresa: campo(form.text, ['Raz[óo]n Social', 'Titular']),
    expediente: campo(form.text, ['N[úu]mero de Expediente ANMAT', 'Expediente N°']),
    contenido: bloque(form.text, 'DESCRIPCI[ÓO]N DEL CAMBIO SOLICITADO', 'SECCI[ÓO]N 5|DOCUMENTACI[ÓO]N ADJUNTA')
  } : null,
  declaracion: decl ? {
    producto: ((decl.text || '').match(/presente en\s+([\s\S]+?),\s*de acuerdo/i) || [])[1]?.replace(/\s+/g, ' ').trim() || campo(decl.text, ['Nombre comercial']),
    empresa: campo(decl.text, ['Laboratorio']) || (decl.text || '').trim().split('\n')[0].trim(),
    contenido: bloque(decl.text, '1\\.\\s*ALCANCE', '2\\.\\s*PAR[ÁA]METROS')
  } : null
};

// ── CONTENIDO REGULATORIO MÍNIMO ──
// Una sección clave sin vocabulario regulatorio ni el IFA (p. ej. un poema o una canción) se objeta.
const VOCAB = ['metodo', 'analitic', 'validacion', 'modificacion', 'cambio', 'especificacion', 'ich', 'potencia',
               'pureza', 'identidad', 'ensayo', 'fabricacion', 'proceso', 'control de calidad', 'envase', 'rotulo', 'prospecto', 'vida util'];
const ifaTxt = normalizar(campo(form?.text || nota?.text || '', ['IFA \\(Ingrediente Farmac[ée]utico Activo\\)', 'IFA'])).split(' (')[0];
function sinDatos(contenido) {
  const t = normalizar(contenido);
  if (t.length < 15) return true;
  const tieneVocab = VOCAB.some(v => t.includes(v));
  const tieneIfa = ifaTxt && ifaTxt.length > 3 && t.includes(ifaTxt.split(' ')[0]);
  return !(tieneVocab || tieneIfa);
}
const seccionesSinDatos = [];
if (datos.nota && sinDatos(datos.nota.contenido)) seccionesSinDatos.push('motivo de la Nota de Presentación');
if (datos.formulario && sinDatos(datos.formulario.contenido)) seccionesSinDatos.push('descripción del cambio del Formulario de Solicitud');
if (datos.declaracion && sinDatos(datos.declaracion.contenido)) seccionesSinDatos.push('alcance del Documento declarado por el regulado');

// ── VERIFICACIONES ──
const tipos = new Set(docs.map(d => d.tipo).filter(Boolean));
const docsFaltantes = ['nota', 'formulario', 'declaracion'].filter(t => !tipos.has(t)).map(t => NOMBRES[t]);
const docsNoReconocidos = docs.filter(d => d.tipo === null);

const clave = s => normalizar(s).replace(/\b(s\.?a\.?|s\.?r\.?l\.?)\b/g, '').replace(/[^a-z0-9]/g, '');
const prods = [...new Set(Object.values(datos).filter(Boolean).map(d => d.producto).filter(Boolean))];
const emps = [...new Set(Object.values(datos).filter(Boolean).map(d => d.empresa).filter(Boolean))];
const prodDistintos = new Set(prods.map(clave)).size > 1;
const empDistintas = new Set(emps.map(clave)).size > 1;

const producto = datos.formulario?.producto || datos.nota?.producto || datos.declaracion?.producto || 'NO IDENTIFICADO';
const empresa = datos.formulario?.empresa || datos.nota?.empresa || datos.declaracion?.empresa || 'NO IDENTIFICADO';
const expedienteDoc = datos.formulario?.expediente || '';
const motivoFinal = (datos.nota?.contenido && !sinDatos(datos.nota.contenido)) ? datos.nota.contenido :
                    (datos.formulario?.contenido && !sinDatos(datos.formulario.contenido)) ? datos.formulario.contenido : 'NO IDENTIFICADO';

// ── DECISIÓN FINAL (reglas fijas; el modelo no decide) ──
const motivos = [];
if (docsFaltantes.length) motivos.push(`Documentos obligatorios faltantes: ${docsFaltantes.join('; ')}.`);
if (archivosRechazados.length) motivos.push(`Archivo(s) en formato no admitido: ${archivosRechazados.join(', ')}.`);
if (docsNoReconocidos.length) motivos.push(`${docsNoReconocidos.length} documento(s) no reconocido(s) como documentación regulatoria.`);
if (seccionesSinDatos.length) motivos.push(`Sin datos regulatorios en: ${seccionesSinDatos.join('; ')}.`);
if (prodDistintos) motivos.push(`El producto no coincide entre documentos: ${prods.join(' / ')}.`);
if (empDistintas) motivos.push(`La empresa no coincide entre documentos: ${emps.join(' / ')}.`);
const esObjecion = motivos.length > 0;

return [{
  json: {
    resultado: esObjecion ? 'OBJECION' : 'VALIDACION',
    nombreArchivo: esObjecion ? `informe_objecion_${timestamp}.docx` : `informe_validacion_${timestamp}.docx`,
    plantillaKey: esObjecion ? 'objecion' : 'aceptable',
    DIA: pad(ahora_art.getUTCDate()),
    MES: meses[ahora_art.getUTCMonth()],
    TIMESTAMP: timestampLegible,
    EXPEDIENTE: expedienteForm || expedienteDoc || 'NO IDENTIFICADO',
    MOTIVO: motivoFinal,
    PRODUCTO: producto,
    EMPRESA: empresa,
    DETALLE: motivos.join(' '),
    respuestaIA: respuesta
  }
}];
