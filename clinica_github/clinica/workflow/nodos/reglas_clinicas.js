// ════════════════════════════════════════════════════════════════════════════════════════════
// Reglas clínicas + ALCOA timestamp — validador FORMAL de trámites CTD (versión CLÍNICA, prueba)
// Principio: Gemini (nodo anterior) solo extrae/sugiere; ESTAS reglas determinísticas deciden.
// Salida central: Asignar a (Calidad | Clínica | Ambas) + dictamen formal (Apto para evaluación | Objetar)
//                 + objeciones (bloqueantes) + observaciones (no bloqueantes) + información.
// No evalúa el fondo científico. No usa informes de evaluación.
// ════════════════════════════════════════════════════════════════════════════════════════════
const VERSION = 'clinica-v1.3 (2026-10-25)';
const raw = $input.first().json || {};
const agregado = $('Obtener todos los textos').first().json || { data: [] };
let splitItems = [];
try { splitItems = $('Split archivos').all(); } catch (e) {}
const expedienteForm = splitItems.find(it => it.json?.expedienteForm)?.json?.expedienteForm || '';
const debug = splitItems.some(it => it.json?.debug);
let archivosRechazados = [];
try { archivosRechazados = $('Code in JavaScript').all().filter(it => it.json.archivoInvalido).map(it => it.json.filename); } catch (e) {}

// ── utilidades ──
const sinTildes = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const norm = s => sinTildes(s).toLowerCase().replace(/[\u2013\u2014]/g, '-').replace(/\s+/g, ' ').trim();
const compacto = s => norm(s).replace(/[^a-z0-9]/g, '');
const digitos = s => (s || '').replace(/\D/g, '');
const unico = a => [...new Set(a)];
const recorte = (s, n = 160) => { s = (s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };

// ── extracción de Gemini (opcional; solo como respaldo y para informar concordancia) ──
let ia = null, iaEstado = 'no disponible';
if (raw.skipped || raw._gemini?.skip) iaEstado = 'omitida (sin_ia=1)';
else {
  const txt = (raw.candidates?.[0]?.content?.parts || []).filter(p => !p.thought).map(p => p.text || '').join('');
  try { ia = JSON.parse(txt.replace(/^```(?:json)?\s*|\s*```$/g, '')); iaEstado = 'ok'; } catch (e) { iaEstado = txt ? 'respuesta no JSON' : 'sin respuesta'; }
}
const iaDoc = nombre => (ia?.documentos || []).find(d => norm(d.archivo) === norm(nombre));

// ════════════════ 1. CLASIFICACIÓN DE DOCUMENTOS (por contenido; el nombre es secundario) ════════════════
const STOP_ES = ['de', 'la', 'el', 'los', 'las', 'que', 'en', 'y', 'para', 'con', 'por', 'del', 'se', 'una', 'un', 'su', 'al', 'es'];
const STOP_EN = ['the', 'of', 'and', 'to', 'in', 'is', 'for', 'with', 'be', 'are', 'this', 'that', 'patients', 'should', 'was', 'were', 'by', 'or'];
function idioma(t) {
  const w = norm(t).split(/[^a-z]+/);
  const es = w.filter(x => STOP_ES.includes(x)).length, en = w.filter(x => STOP_EN.includes(x)).length;
  if (es + en < 8) return 'indeterminado';
  return en > es ? 'en' : 'es';
}
function tipoDoc(t, nombre) {
  const h = norm(t.slice(0, 700)), f = norm(t), n = norm(nombre);
  if (/highlights of prescribing information|full prescribing information/.test(h) || /\d{6}s\d{3}lbl/.test(n)) return 'referencia_fda';
  if (/ficha tecnica o resumen de las caracteristicas del producto|summary of product characteristics|agencia europea de medicamentos|european medicines agency/.test(f.slice(0, 3000)) || /epar/.test(n)) return 'referencia_ema';
  if (/product monograph|monographie de produit/.test(h)) return 'referencia_otra_agencia';
  if (/registro de especialidades medicinales|anexo iii certificado|datos de la especialidad medicinal/.test(h)) return 'certificado';
  if (/nota de presentacion|de nuestra (mayor )?consideracion|concepto del recibo|motivo del tramite/.test(h)) return 'nota';
  if (/formulario de solicitud|ficha de modificaciones|alcance de la aplicacion|formulario soli/.test(h)) return 'formulario';
  if (/declaracion jurada/.test(h) && /unicos cambios/.test(f)) return 'ddjj_cambios';
  if (/declaracion jurada/.test(h) && /no se encuentra impactada|no hay modificaciones|no modifica/.test(f)) return 'ddjj_no_impactada';
  if (/aspectos clinicos generales|resumen clinico|clinical overview|modulo 2\.5|module 2\.5|descripcion general clinica/.test(h)) return 'resumen_clinico';
  if (/documento declarado por el regulado|3\.2\.[ps]\.\d/.test(h)) return 'soporte_calidad';
  if (/informacion para el paciente|lea todo este prospecto|prospecto: informacion para el usuario/.test(h)) return 'info_paciente';
  if (/rotulo|estuche|etiqueta del/.test(h)) return 'rotulo';
  if (/prospecto|informacion para el profesional/.test(h) || (/posologia/.test(f) && /contraindicaciones/.test(f))) return 'prospecto';
  if (/company core data sheet|core data sheet/.test(h)) return 'documento_empresa';
  return 'otro';
}
const RE_IF = /IF-\d{4}-\d{5,}-APN-[A-Z]+#ANMAT/;
const RE_GLOBO = /(Comentado|Commented)\s*\[[A-Za-z]{1,4}\d+\]|^\s*(Con formato|Formatted):/m;
const RE_FECHA_DUP = /revisi[oó]n:?\s*[a-záéíóú]+\s*\d{4}\s*[a-záéíóú]+\s*\d{4}/i;
function rolTexto(t) {
  const ev = [];
  if (RE_IF.test(t)) ev.push('sello_IF');
  if (RE_GLOBO.test(t)) ev.push('globos_comentario');
  if (/CONTROL DE CAMBIOS/.test(t)) ev.push('encabezado_control_cambios');
  if (RE_FECHA_DUP.test(t)) ev.push('fechas_duplicadas');
  const rol = ev.includes('sello_IF') && ev.length === 1 ? 'aprobado' : ev.some(e => e !== 'sello_IF') ? 'control_cambios' : 'proyecto';
  return { rol, ev };
}
function rolNombre(nombre) {
  const n = norm(nombre);
  if (/aprobad/.test(n)) return 'aprobado';
  if (/ctrol|control|cambios|working/.test(n)) return 'control_cambios';
  if (/proyect/.test(n)) return 'proyecto';
  return null;
}
const ES_TEXTO = { prospecto: 'prospecto', info_paciente: 'ip', rotulo: 'rotulo' };
const NOMBRE_TEXTO = { prospecto: 'Prospecto', ip: 'Información para el paciente', rotulo: 'Rótulos' };

const docs = (agregado.data || []).map((d, i) => {
  const text = d.text || '', archivo = d.fileName || `documento_${i + 1}`;
  let tipo = tipoDoc(text, archivo), fuenteTipo = 'reglas';
  if (tipo === 'otro' && iaDoc(archivo)?.tipo_canonico) { tipo = iaDoc(archivo).tipo_canonico.replace('info_paciente', 'info_paciente'); fuenteTipo = 'IA'; }
  const doc = { archivo, text, tipo, fuenteTipo, idioma: idioma(text), texto: ES_TEXTO[tipo] || null, hash: compacto(text).slice(0, 4000) };
  if (doc.texto) { const r = rolTexto(text); doc.rol = r.rol; doc.evidenciaRol = r.ev; doc.rolNombre = rolNombre(archivo); }
  return doc;
});
const porTipo = t => docs.filter(d => d.tipo === t);
const objeciones = [], observaciones = [], informacion = [];
const objetar = (codigo, regla, detalle, archivo) => objeciones.push({ codigo, regla, detalle, archivo: archivo || '' });
const observar = (codigo, regla, detalle, archivo) => observaciones.push({ codigo, regla, detalle, archivo: archivo || '' });
const informar = (codigo, detalle, archivo) => informacion.push({ codigo, detalle, archivo: archivo || '' });

if (archivosRechazados.length) objetar('FORMATO', 'R-FMT', `Archivo(s) en formato no admitido: ${archivosRechazados.join(', ')}. Presentar en PDF.`);
if (!docs.length) objetar('SIN_DOCUMENTOS', 'R-DOC', 'No se recibieron documentos legibles.');

// ════════════════ 2. CERTIFICADO REM (fuente de verdad) ════════════════
function campo(t, etiquetas) {
  for (const et of etiquetas) {
    const m = (t || '').match(new RegExp('(?:^|\\n)[ \\t•\\-]*' + et + '[ \\t]*:[ \\t]*([^\\n]+)', 'i'));
    if (m && m[1].trim()) return m[1].trim();
  }
  return '';
}
const certDoc = porTipo('certificado')[0];
const cert = { presente: !!certDoc, fuente: {} };
if (certDoc) {
  const t = certDoc.text;
  cert.nombre = campo(t, ['Nombre comercial']); cert.ifa = campo(t, ['Nombre Gen[ée]rico \\(IFA/s\\)', 'Nombre/s gen[ée]rico/s', 'Nombre gen[ée]rico', 'IFA']);
  cert.concentracion = campo(t, ['Concentraci[óo]n(?:/es)?']); cert.forma = campo(t, ['Forma farmac[ée]utica']);
  cert.titular = campo(t, ['Raz[óo]n Social', 'Titular']);
  cert.numero = ((t.match(/CERTIFICADO\s*N[°ºo]\.?\s*([\d\.\s]{4,9})/i) || [])[1] || '').trim();
  cert.vida = campo(t, ['Per[íi]odo de vida [úu]til']); cert.conservacion = campo(t, ['Forma de conservaci[óo]n']);
  cert.elaborador = campo(t, ['Elaborador del producto terminado', 'Elaborador']);
  const c2 = ia?.certificado || {};
  for (const [k, kia] of [['nombre', 'nombre_comercial'], ['ifa', 'ifa'], ['concentracion', 'concentracion'], ['forma', 'forma_farmaceutica'], ['titular', 'titular'], ['numero', 'n_certificado']]) {
    cert.fuente[k] = cert[k] ? 'reglas' : (c2[kia] ? 'IA' : 'no encontrado');
    if (!cert[k] && c2[kia]) cert[k] = String(c2[kia]);
  }
} else {
  objetar('FALTA_CERT', 'R-CERT-0', 'No se presentó el Certificado REM del producto (fuente de verdad de nombre comercial, IFA, concentración, forma farmacéutica, titular y N° de certificado).');
}

// ── normalizadores para la congruencia ──
const nNombre = s => compacto((s || '').replace(/[®™]/g, ''));
const nIfa = s => compacto(s);
const nConc = s => norm(s).replace(/,/g, '.').replace(/\s+/g, '').replace(/mililitros?/g, 'ml');
const SINON = [[/perfusion/g, 'infusion'], [/endovenos[ao]/g, 'intravenosa'], [/inyeccion/g, 'inyectable'], [/liofilizado/g, 'liofilizado']];
const nForma = s => { let x = norm(s); for (const [a, b] of SINON) x = x.replace(a, b); return x.replace(/[^a-z]/g, ''); };
const nTit = s => norm(s).replace(/\b(s\.?\s?a\.?\s?(q\.?\s?e?\s?i\.?)?|s\.?\s?r\.?\s?l\.?|s\.?\s?a\.?\s?i\.?\s?c\.?)(?=\s|$|,|\.)/g, '').replace(/[^a-z0-9]/g, '');
const RE_CONC = /\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ui|u)\s*\/\s*\d*(?:[.,]\d+)?\s*(?:ml|dosis)/gi;

// ════════════════ 3. CONGRUENCIA CON EL CERTIFICADO (nota, formulario, DDJJ y textos propuestos) ════════════════
const incong = [];
function cotejar(dato, valorDoc, valorCert, fn, archivo) {
  if (!valorDoc || !valorCert) return;
  if (fn(valorDoc) !== fn(valorCert)) incong.push({ dato, archivo, documento: valorDoc, certificado: valorCert });
}
if (cert.presente) {
  for (const d of [...porTipo('nota'), ...porTipo('formulario')]) {
    const t = d.text;
    cotejar('nombre comercial', campo(t, ['Nombre comercial', 'Producto']), cert.nombre, nNombre, d.archivo);
    cotejar('IFA', campo(t, ['IFA(?: \\([^)]*\\))?', 'Nombre gen[ée]rico(?: \\(IFA\\))?', 'Principio activo']), cert.ifa, nIfa, d.archivo);
    cotejar('concentración', campo(t, ['Concentraci[óo]n(?:/es)?']), cert.concentracion, nConc, d.archivo);
    cotejar('forma farmacéutica', campo(t, ['Forma farmac[ée]utica']), cert.forma, nForma, d.archivo);
    cotejar('titular', campo(t, ['Titular(?: del (?:registro|certificado))?', 'Raz[óo]n social', 'Solicitante']), cert.titular, nTit, d.archivo);
    cotejar('N° de certificado', campo(t, ['Certificado N[°ºo]\\.?', 'N[°ºo]\\.? de certificado']), cert.numero, digitos, d.archivo);
  }
  const propios = docs.filter(d => (d.texto && d.rol === 'proyecto') || /^ddjj/.test(d.tipo));
  for (const d of propios) {
    const t = d.text, cab = t.slice(0, 450);
    for (const m of t.matchAll(/Certificado\s*N[°ºo]\.?\s*:?\s*([\d][\d\.\s]{3,8}\d)/gi)) cotejar('N° de certificado', m[1], cert.numero, digitos, d.archivo);
    if (!d.texto) continue;
    if (cert.nombre && !nNombre(cab).includes(nNombre(cert.nombre))) {
      const otro = (cab.match(/^\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\- ]{2,40})®/m) || [])[1] || '(no figura)';
      incong.push({ dato: 'nombre comercial', archivo: d.archivo, documento: otro.trim(), certificado: cert.nombre });
    }
    if (cert.ifa && !nIfa(cab).includes(nIfa(cert.ifa))) incong.push({ dato: 'IFA', archivo: d.archivo, documento: '(no figura en el encabezado)', certificado: cert.ifa });
    for (const m of cab.match(RE_CONC) || []) cotejar('concentración', m, cert.concentracion, nConc, d.archivo);
    if (cert.forma && d.texto !== 'rotulo' && !nForma(cab).includes(nForma(cert.forma))) incong.push({ dato: 'forma farmacéutica', archivo: d.archivo, documento: '(no coincide en el encabezado)', certificado: cert.forma });
    const tit = (t.match(/Titular:\s*([^,\n]+(?:S\.?\s?A\.?|S\.?\s?R\.?\s?L\.?)?)/i) || [])[1];
    if (tit) cotejar('titular', tit, cert.titular, nTit, d.archivo);
  }
  for (const x of incong) objetar('INCONGRUENCIA', 'R-CERT-3', `${x.dato}: «${x.documento}» en ${x.archivo} no coincide con el certificado REM («${x.certificado}»).`, x.archivo);
}

// ════════════════ 4. IDIOMA ════════════════
for (const d of docs) {
  if (d.idioma !== 'en') continue;
  if (/^referencia_/.test(d.tipo)) continue;   // referencias de agencias (EMA/FDA/otras): se aceptan
  objetar('IDIOMA', 'R-IDI-1', `El documento «${d.archivo}» (${d.tipo.replace(/_/g, ' ')}) está en idioma no español y no es una referencia de agencia. Se solicita presentarlo en idioma español.`, d.archivo);
}
for (const d of docs.filter(d => /^referencia_/.test(d.tipo))) {
  informar('REF_AGENCIA', `Se recibió ${d.tipo === 'referencia_fda' ? 'el prospecto/label de FDA' : d.tipo === 'referencia_ema' ? 'la información del producto de EMA (EPAR/SmPC)' : 'una referencia de otra agencia'} (${d.idioma === 'en' ? 'en inglés' : 'en español'}) como referencia; es opcional y no se evalúa.`, d.archivo);
}

// ════════════════ 5. TABLA DE MODIFICACIONES (referencia del alcance) ════════════════
const SEC_TABLA = [
  ['CONTRAINDICACIONES', /contraindicac/], ['INDICACIONES', /(?<!contra)indicaci|que es .{0,40}para que|para que se utiliza/],
  ['POSOLOGIA', /posolog|\bdosis\b|modo de administracion|forma de administracion|como usar/], ['SOBREDOSIS', /sobredosi/],
  ['ADVERTENCIAS', /advertencia|precaucion|que necesita saber|antes de usar/], ['INTERACCIONES', /interacci/],
  ['POBLACIONES', /embarazo|lactancia|fertilidad|poblaciones|pediatr/], ['RAM', /reacciones adversas|efectos adversos|posibles efectos|efectos secundarios|\bram\b|poscomercializ/],
  ['PROPIEDADES', /propiedades|farmacocin|farmacodin|mecanismo de accion|caracteristicas farmacol/], ['ESTUDIOS', /estudios clinicos/],
  ['COMPOSICION', /formula|composicion|excipiente/], ['CONSERVACION', /conservacion|almacenamiento|vida util|periodo de validez/],
  ['PRESENTACION', /presentacion|contenido del envase|^contenido\b/], ['ELABORADOR', /elaborad|fabricante|sitio de fabricacion/],
  ['ESPECIFICACIONES', /especificacion|metodo analitico/], ['ACCION', /accion terapeutica/]];
const CLINICAS = ['INDICACIONES', 'POSOLOGIA', 'CONTRAINDICACIONES', 'ADVERTENCIAS', 'INTERACCIONES', 'POBLACIONES', 'RAM', 'SOBREDOSIS', 'PROPIEDADES', 'ESTUDIOS', 'ACCION'];
const CALIDAD = ['COMPOSICION', 'CONSERVACION', 'ELABORADOR', 'ESPECIFICACIONES', 'PRESENTACION'];
function docDeLinea(l, sig) {
  if (/datos caracteristicos/.test(l)) return 'ficha';
  if (/paciente/.test(l)) return 'ip';
  if (/informacion para\s*$|informacion para (?!el profesional)/.test(l) && /^\s*(el )?(paciente|usuario)/.test(sig || '')) return 'ip';   // celda partida en dos renglones
  if (/prospecto|profesional/.test(l)) return 'prospecto';
  if (/rotulo|estuche|etiqueta/.test(l)) return 'rotulo';
  return null;
}
function regionTabla(t, tipo) {
  const L = t.split('\n');
  let i0 = -1, i1 = L.length;
  const ini = tipo === 'ddjj_cambios' ? /unicos cambios/ : /tabla de modificaciones|ficha de modificaciones|datos afectados|antecedentes y descripcion|autorizado vs propuesto|resumen de los cambios|cuadro comparativo|modificacion solicitada/;
  for (let i = 0; i < L.length; i++) { if (i0 < 0 && ini.test(norm(L[i]))) { i0 = i; continue; } if (i0 >= 0 && /documentacion soporte|^se declara que los nuevos textos|^firma/.test(norm(L[i]))) { i1 = i; break; } }
  return i0 < 0 ? [] : L.slice(i0, i1).map(norm);
}
function parsearTabla() {
  const filas = [], estadoDoc = {}, fuentes = [];
  let nuevaInd = false;
  for (const d of [...porTipo('formulario'), ...porTipo('ddjj_cambios')]) {
    const L = regionTabla(d.text, d.tipo);
    if (!L.length) continue;
    fuentes.push(d.archivo);
    let ctx = null;
    for (let i = 0; i < L.length; i++) {
      const l = L[i];
      if (/nueva indicacion/.test(l)) nuevaInd = true;
      const dl = docDeLinea(l, L[i + 1]);
      const sin = /sin modificacion|no hay modificaciones|\bn\/a\b|no afectad|no se encuentra impactad/.test(l), con = /con modificacion/.test(l);
      if (dl) { ctx = dl; if (dl !== 'ficha' && (sin || con)) estadoDoc[dl] = sin ? 'sin' : 'con'; }
      else if (sin && ctx && ctx !== 'ficha' && /datos afectados/.test(l)) estadoDoc[ctx] = 'sin';
      const limpiar = x => (x || '').replace(/informacion para el (paciente|profesional)|prospecto|rotulos?|datos caracteristicos|aprobado:.*$/g, ' ');
      const resto = limpiar(l), sig = limpiar(L[i + 1]);
      // una celda puede partirse en dos renglones ("Posibles efectos / adversos"): se acepta el término que EMPIEZA en este renglón
      const secs = SEC_TABLA.filter(([, re]) => { const m = (resto + ' ' + sig).match(re); return m && m.index < resto.length; }).map(([k]) => k);
      if (!secs.length) continue;
      if (sin) continue;   // fila de la ficha marcada SIN MODIFICACIÓN / N/A
      const docFila = ctx || 'ficha';
      const contexto = l + ' ' + (L[i + 1] || '') + ' ' + (L[i + 2] || '');
      for (const s of secs) filas.push({ documento: docFila, seccion: s, estado: 'con', texto: recorte(l, 120), remiteDisposicion: /disposicion|ya aprobad/.test(contexto),
                                         sinCambioCuantitativo: /sin cambio cuali|efecto conocido/.test(contexto), fuente: 'reglas' });
    }
  }
  for (const f of filas) if (f.documento !== 'ficha' && !estadoDoc[f.documento]) estadoDoc[f.documento] = 'con';
  return { filas, estadoDoc, fuentes, nuevaInd };
}
const tabla = parsearTabla();
tabla.origen = 'reglas';
if (!tabla.filas.length && ia?.tabla_modificaciones?.filas?.length) {   // respaldo: filas extraídas por Gemini
  const mapDoc = { prospecto: 'prospecto', info_paciente: 'ip', rotulo: 'rotulo', ficha: 'ficha' };
  for (const f of ia.tabla_modificaciones.filas) {
    if (f.estado === 'sin_modificacion') { if (mapDoc[f.documento] && mapDoc[f.documento] !== 'ficha') tabla.estadoDoc[mapDoc[f.documento]] = tabla.estadoDoc[mapDoc[f.documento]] || 'sin'; continue; }
    const doc = mapDoc[f.documento] || 'ficha';
    tabla.filas.push({ documento: doc, seccion: f.seccion_canonica || 'OTRA', estado: 'con', texto: recorte(f.resumen || f.seccion_original, 120),
                       remiteDisposicion: !!f.remite_a_disposicion_aprobada, sinCambioCuantitativo: f.es_dato_de_calidad === false && f.seccion_canonica === 'COMPOSICION', fuente: 'IA' });
    if (doc !== 'ficha') tabla.estadoDoc[doc] = 'con';
  }
  if (ia.tabla_modificaciones.declara_nueva_indicacion) tabla.nuevaInd = true;
  tabla.origen = 'IA (respaldo)';
}
const docsDeclarados = Object.keys(tabla.estadoDoc).filter(k => tabla.estadoDoc[k] === 'con');
if (!tabla.filas.length && !docsDeclarados.length) {
  objetar('SIN_TABLA', 'R-TAB-1', 'No se identificó la tabla de modificaciones (formulario 1.2 o declaración jurada de únicos cambios); no se puede verificar el alcance del trámite.');
}

// ════════════════ 6. TEXTOS: roles, dos versiones (CC + proyecto) y cambios por sección ════════════════
const SEC_TXT = [
  ['COMPOSICION', /^(formula|composicion|composicion cuali)/], ['ACCION', /^accion terapeutica/],
  ['INDICACIONES', /^(indicaciones|1\.? ?¿?que es )/], ['PROPIEDADES', /^(caracteristicas farmacologicas|propiedades farmaco|farmacologia clinica)/],
  ['POSOLOGIA', /^(posologia|dosis y administracion|modo de administracion|3\.? ?¿?como (usar|se usa|se administra))/],
  ['CONTRAINDICACIONES', /^contraindicaciones/], ['ADVERTENCIAS', /^(advertencias|precauciones|2\.? ?¿?que necesita saber)/],
  ['INTERACCIONES', /^interacciones/], ['POBLACIONES', /^(embarazo|lactancia|fertilidad|uso en poblaciones)/],
  ['RAM', /^(reacciones adversas|efectos adversos|4\.? ?posibles efectos adversos)/], ['SOBREDOSIS', /^sobredosi/],
  ['ESTUDIOS', /^estudios clinicos/], ['PRESENTACION', /^(presentacion|contenido$|6\.? ?contenido del envase)/],
  ['CONSERVACION', /^(conservacion|condiciones de conservacion|almacenamiento|5\.? ?conservacion de)/], ['ELABORADOR', /^elaborado (por|en)/],
  ['PIE', /^(especialidad medicinal autorizada|director tecnico|titular:|fecha de ultima revision)/]];
const RUIDO = /IF-\d{4}-\d+-APN|^P[aá]gina \d+|P[aá]gina firmada digitalmente|^CONTROL DE CAMBIOS$|^(Comentado|Commented)\s*\[|^(Con formato|Formatted):|Firmado digitalmente|Digitally signed|^Fecha de [uú]ltima revisi[oó]n/i;
function secciones(t) {
  const out = {}, globos = []; let sec = 'ENCABEZADO';
  for (const linea of t.split('\n')) {
    const l = linea.trim();
    if (/^(Comentado|Commented)\s*\[|^(Con formato|Formatted):/i.test(l)) { globos.push(sec); continue; }   // globo de Word: marca de cambio en la sección
    if (!l || RUIDO.test(l)) continue;
    const n = norm(l);
    let h = SEC_TXT.find(([k, re]) => re.test(n) && (k === 'PIE' || k === 'ELABORADOR' || (n.length <= 70 && !/\.$/.test(n))));
    if (h && sec === 'PIE' && h[0] !== 'PIE') h = null;          // el pie legal cierra el texto
    if (h) {
      sec = h[0];
      const soloEncabezado = sec !== 'PIE' && !(sec === 'ELABORADOR' && n.length > 16);
      if (soloEncabezado) continue;
    }
    (out[sec] = out[sec] || []).push(n);
  }
  return { out, globos };
}
const cantidades = lineas => unico((lineas || []).flatMap(l => [...l.matchAll(/([a-z][a-z0-9 \-]{2,40}?)\s+(\d+(?:[.,]\d+)?)\s*(mg|mcg|g|ml|ui)\b/g)].map(m => compacto(m[1]) + '=' + m[2].replace(',', '.') + m[3]))).sort().join('|');
const numCons = lineas => unico((lineas || []).join(' ').match(/\d+(?:[.,]\d+)?\s*(?:°\s?c|º\s?c|meses|dias|horas)/g) || []).map(x => x.replace(/\s/g, '')).sort().join('|');
const numPres = lineas => unico((lineas || []).join(' ').match(/\d+(?:[.,]\d+)?\s*(?:ml|viales|jeringas|lapiceras|unidades)/g) || []).sort().join('|');

const textos = {};
for (const d of docs.filter(d => d.texto)) (textos[d.texto] = textos[d.texto] || []).push(d);
const cambios = [];      // {doc, seccion, base, tipo}
const resumenTextos = {};
for (const [x, lista] of Object.entries(textos)) {
  const A = lista.filter(d => d.rol === 'aprobado'), CC = lista.filter(d => d.rol === 'control_cambios'), P = lista.filter(d => d.rol === 'proyecto');
  resumenTextos[x] = { aprobado: A.map(d => d.archivo), control_cambios: CC.map(d => d.archivo), proyecto: P.map(d => d.archivo) };
  for (const d of lista) if (d.rolNombre && d.rolNombre !== d.rol)
    observar('ROL_NOMBRE', 'R-ROL-1', `«${d.archivo}»: el nombre sugiere ${d.rolNombre.replace('_', ' ')}, pero por contenido es ${d.rol.replace('_', ' ')} (${d.evidenciaRol.join(', ') || 'sin marcas de revisión'}). Se tomó el rol por contenido.`, d.archivo);
  const p = P[P.length - 1];
  const base = A[A.length - 1] || CC[CC.length - 1];
  if (!p || !base) continue;
  const SP = secciones(p.text), SB = secciones(base.text), sp = SP.out, sb = SB.out;
  const baseEsCCB = !A.length && CC.length && compacto(CC[CC.length - 1].text.replace(/CONTROL DE CAMBIOS/g, '')) === compacto(p.text);
  if (baseEsCCB) { observar('ALCANCE_NO_VERIFICABLE', 'R-ROL-3', `${NOMBRE_TEXTO[x]}: el control de cambios no muestra diferencias de texto con el proyecto (marcas solo visuales) y no se presentó el aprobado; el alcance no pudo verificarse por texto.`); continue; }
  for (const s of unico([...Object.keys(sp), ...Object.keys(sb)])) {
    const a = (sb[s] || []).join(' '), b = (sp[s] || []).join(' ');
    // sin aprobado, el CC (estilo Word) conserva lo eliminado pero no distingue lo agregado: el globo de comentario marca la sección cambiada
    const porGlobo = !A.length && SB.globos.includes(s);
    if (compacto(a) === compacto(b) && !porGlobo) continue;
    let tipo;
    if (s === 'ENCABEZADO' || s === 'PIE') tipo = 'administrativo';
    else if (s === 'COMPOSICION') tipo = cantidades(sb[s]) !== cantidades(sp[s]) ? 'calidad' : 'clinico';
    else if (s === 'CONSERVACION') tipo = numCons(sb[s]) !== numCons(sp[s]) ? 'calidad' : 'clinico';
    else if (s === 'PRESENTACION') tipo = numPres(sb[s]) !== numPres(sp[s]) ? 'calidad' : 'administrativo';
    else if (s === 'ELABORADOR') tipo = 'calidad';
    else tipo = 'clinico';
    const agregado = compacto(b).length > compacto(a).length;
    cambios.push({ doc: x, seccion: s, base: A.length ? 'aprobado→proyecto' : 'control de cambios→proyecto', tipo, agrega: agregado, archivo: p.archivo });
  }
}

// R-DOC-2: cada texto declarado como modificado debe tener versión con control de cambios Y proyecto limpio
const docsConCambio = unico([...docsDeclarados, ...cambios.filter(c => c.tipo !== 'administrativo').map(c => c.doc)]);
for (const x of docsDeclarados) {
  const r = resumenTextos[x] || { control_cambios: [], proyecto: [] };
  if (!r.control_cambios.length) objetar('FALTA_CC', 'R-DOC-2', `${NOMBRE_TEXTO[x]}: declarado como modificado en la tabla, pero no se presentó la versión con control de cambios.`);
  if (!r.proyecto.length) objetar('FALTA_P', 'R-DOC-2', `${NOMBRE_TEXTO[x]}: declarado como modificado en la tabla, pero no se presentó el proyecto limpio${r.control_cambios.length > 1 ? ' (el archivo presentado como proyecto conserva marcas de control de cambios)' : ''}.`);
}

// R-TAB-3: todo cambio detectable en los textos debe figurar en la tabla
function declarado(c) {
  return tabla.filas.some(f => f.seccion === c.seccion && (f.documento === c.doc || f.documento === 'ficha'));
}
const noDeclarados = cambios.filter(c => c.tipo !== 'administrativo' && !declarado(c));
for (const c of noDeclarados)
  objetar('NO_DECLARADO', 'R-TAB-3', `${NOMBRE_TEXTO[c.doc]} — sección ${c.seccion.toLowerCase()}: hay un cambio en el texto (${c.base}) que no figura en la tabla de modificaciones.`, c.archivo);
const admin = cambios.filter(c => c.tipo === 'administrativo');
if (admin.length) informar('CAMBIOS_ADMIN', `Cambios administrativos detectados (no requieren fila en la tabla): ${unico(admin.map(c => NOMBRE_TEXTO[c.doc] + ' ' + c.seccion.toLowerCase())).join('; ')}.`);
for (const f of tabla.filas.filter(f => f.documento !== 'ficha' && CLINICAS.includes(f.seccion)))
  if ((textos[f.documento] || []).some(d => d.rol === 'proyecto') && !cambios.some(c => c.doc === f.documento && c.seccion === f.seccion) && resumenTextos[f.documento]?.aprobado?.length)
    observar('DECLARADO_NO_ENCONTRADO', 'R-TAB-2', `${NOMBRE_TEXTO[f.documento]} — ${f.seccion.toLowerCase()}: figura en la tabla pero no se detectó el cambio en el texto.`);

// ════════════════ 7. NOTA ↔ TABLA (la nota no es DDJJ: solo observación) ════════════════
const notaDoc = porTipo('nota')[0];
if (notaDoc) {
  const L = notaDoc.text.split('\n').map(norm);
  let i0 = L.findIndex(l => /textos que se presentan|se presentan los siguientes|documentacion que se adjunta/.test(l));
  const zona = i0 >= 0 ? L.slice(i0 + 1, i0 + 8).filter(l => /^[•\-\*·]|^\d/.test(l) || docDeLinea(l)) : L.filter(l => /^[•\-\*·]/.test(l));
  const enNota = unico(zona.map(docDeLinea).filter(x => x && x !== 'ficha'));
  const enTabla = docsDeclarados;
  const faltan = enTabla.filter(x => !enNota.includes(x)), sobran = enNota.filter(x => !enTabla.includes(x));
  if (enNota.length && (faltan.length || sobran.length))
    observar('NOTA_TABLA', 'R-TAB-4', `La nota de presentación no coincide con la tabla de modificaciones: ${faltan.length ? 'la nota no menciona ' + faltan.map(x => NOMBRE_TEXTO[x]).join(', ') : ''}${faltan.length && sobran.length ? '; ' : ''}${sobran.length ? 'la nota menciona ' + sobran.map(x => NOMBRE_TEXTO[x]).join(', ') + ' que no figura(n) en la tabla' : ''}. La nota no es declaración jurada: se toma la tabla como referencia.`, notaDoc.archivo);
}

// ════════════════ 8. RESUMEN CLÍNICO / NUEVA INDICACIÓN ════════════════
const rc = porTipo('resumen_clinico');
const nuevaIndicacion = tabla.nuevaInd || /nueva indicacion/.test(norm(notaDoc?.text || '')) || cambios.some(c => c.seccion === 'INDICACIONES' && c.doc === 'prospecto' && c.agrega);
for (const d of rc) informar('RC_RECIBIDO', `Se recibió resumen clínico (${d.idioma === 'en' ? 'en inglés' : 'en español'}); se informa como documentación adicional (plus).`, d.archivo);
if (nuevaIndicacion && !rc.length) observar('SIN_RC', 'R-RC-1', 'El trámite incorpora una nueva indicación y no se adjuntó resumen clínico (Módulo 2.5/2.7). Observación no bloqueante.');

// ════════════════ 9. ASIGNACIÓN Calidad / Clínica / Ambas ════════════════
const K = cambios.some(c => c.tipo === 'clinico') ||
          tabla.filas.some(f => CLINICAS.includes(f.seccion)) ||
          tabla.filas.some(f => f.seccion === 'COMPOSICION' && f.sinCambioCuantitativo);
const Cdiff = cambios.filter(c => c.tipo === 'calidad' && !(c.seccion === 'ELABORADOR' && tabla.filas.some(f => f.seccion === 'ELABORADOR' && f.remiteDisposicion)));
const Ctab = tabla.filas.filter(f => ['COMPOSICION', 'CONSERVACION', 'ELABORADOR', 'ESPECIFICACIONES'].includes(f.seccion) && !f.remiteDisposicion && !f.sinCambioCuantitativo);
const C = Cdiff.length > 0 || Ctab.length > 0;
let asignarA = K && C ? 'Ambas' : C ? 'Calidad' : K ? 'Clínica' : (docsConCambio.some(x => x !== 'rotulo') ? 'Clínica' : 'Calidad');
const fundamento = [];
if (K) fundamento.push('cambios en textos clínicos (' + unico([...cambios.filter(c => c.tipo === 'clinico').map(c => c.seccion), ...tabla.filas.filter(f => CLINICAS.includes(f.seccion)).map(f => f.seccion)]).map(s => s.toLowerCase()).join(', ') + ')');
if (C) fundamento.push('cambio de datos de calidad respecto del certificado/aprobado (' + unico([...Cdiff.map(c => c.seccion), ...Ctab.map(f => f.seccion)]).map(s => s.toLowerCase()).join(', ') + ')');
if (!K && !C) fundamento.push('solo cambios administrativos; criterio por defecto según textos afectados');

// Rama Calidad (secundaria, informativa): conserva la idea del validador v2 (documentación de soporte del Módulo 3)
const ramaCalidad = { aplica: asignarA !== 'Clínica' };
if (ramaCalidad.aplica) {
  const sop = porTipo('soporte_calidad');
  ramaCalidad.soporte_modulo3 = sop.map(d => d.archivo);
  ramaCalidad.resultado = sop.length ? 'Se identificó documentación de soporte de calidad (Módulo 3) para la evaluación de Calidad.' : 'No se identificó documentación de soporte del Módulo 3; Calidad deberá requerirla.';
  if (!sop.length) observar('CALIDAD_SIN_SOPORTE', 'R-CAL-1', 'Derivación a Calidad: no se identificó documentación de soporte del Módulo 3 para el cambio de datos de calidad.');
}

// ════════════════ 10. DUPLICADOS Y OTROS HALLAZGOS (observaciones) ════════════════
const vistos = {};
for (const d of docs) { if (d.hash.length < 50) continue; if (vistos[d.hash]) observar('DUPLICADO', 'R-ROL-4', `«${d.archivo}» es idéntico a «${vistos[d.hash]}».`, d.archivo); else vistos[d.hash] = d.archivo; }
for (const d of docs.filter(d => d.tipo === 'otro')) observar('NO_RECONOCIDO', 'R-DOC-0', `No se pudo clasificar «${d.archivo}» como documento regulatorio conocido.`, d.archivo);

// ════════════════ 11. DICTAMEN + salida compatible con la copia de prueba ════════════════
const esObjecion = objeciones.length > 0;
const dictamen = esObjecion ? 'Objetar' : 'Apto para evaluación';
const ahora = new Date(Date.now() - 3 * 3600 * 1000);
const pad = n => String(n).padStart(2, '0');
const ts = `${ahora.getUTCFullYear()}${pad(ahora.getUTCMonth() + 1)}${pad(ahora.getUTCDate())}_${pad(ahora.getUTCHours())}${pad(ahora.getUTCMinutes())}${pad(ahora.getUTCSeconds())}`;
const tsLeg = `${pad(ahora.getUTCDate())}/${pad(ahora.getUTCMonth() + 1)}/${ahora.getUTCFullYear()} ${pad(ahora.getUTCHours())}:${pad(ahora.getUTCMinutes())}:${pad(ahora.getUTCSeconds())} (ART UTC-3)`;
const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const notaT = notaDoc?.text || '';
const motivo = recorte((notaT.match(/MOTIVO DEL TR[ÁA]MITE:?\s*([\s\S]+?)(?:\n\s*\n|Textos que se presentan|Se declara|$)/i) || [])[1] || campo(notaT, ['Ref\\.?']) || 'NO IDENTIFICADO', 400);
const iaSug = ia?.sugerencia || null;
const sal = {
  version: VERSION,
  asignar_a: asignarA,
  dictamen,
  resultado: esObjecion ? 'OBJECION' : 'VALIDACION',
  nombreArchivo: esObjecion ? `informe_objecion_${ts}.docx` : `informe_validacion_${ts}.docx`,
  plantillaKey: esObjecion ? 'objecion' : 'aceptable',
  DIA: pad(ahora.getUTCDate()), MES: meses[ahora.getUTCMonth()], TIMESTAMP: tsLeg,
  EXPEDIENTE: expedienteForm || campo(notaT, ['Expediente N[°ºo]\\.?', 'Expediente']) || 'NO IDENTIFICADO',
  MOTIVO: motivo,
  PRODUCTO: cert.nombre || campo(notaT, ['Nombre comercial']) || 'NO IDENTIFICADO',
  EMPRESA: cert.titular || campo(notaT, ['Titular']) || 'NO IDENTIFICADO',
  ASIGNAR_A: asignarA, DICTAMEN: dictamen,
  DETALLE: esObjecion ? objeciones.map((o, i) => `${i + 1}. ${o.detalle}`).join(' ') : 'Sin objeciones formales.',
  OBSERVACIONES: observaciones.map((o, i) => `${i + 1}. ${o.detalle}`).join(' '),
  objeciones, observaciones, informacion,
  fundamento_asignacion: fundamento.join('; '),
  certificado: cert,
  tabla_modificaciones: { origen: tabla.origen, ubicacion: tabla.fuentes, textos_declarados: docsDeclarados, filas: tabla.filas, nueva_indicacion: nuevaIndicacion },
  textos: resumenTextos,
  cambios_detectados: cambios.map(c => ({ ...c, declarado: c.tipo === 'administrativo' ? 'no requiere' : declarado(c) })),
  documentos: docs.map(d => ({ archivo: d.archivo, tipo: d.tipo, rol: d.rol || null, idioma: d.idioma, clasificado_por: d.fuenteTipo, evidencia_rol: d.evidenciaRol || [] })),
  rama_calidad: ramaCalidad,
  extraccion_ia: { estado: iaEstado, sugerencia_asignacion: iaSug?.asignar_a || null, coincide_asignacion: iaSug?.asignar_a ? norm(iaSug.asignar_a) === norm(asignarA) : null,
                   filas_tabla_ia: ia?.tabla_modificaciones?.filas?.length ?? null, filas_tabla_reglas: tabla.origen === 'reglas' ? tabla.filas.length : 0,
                   modelo: raw._gemini?.modelo || null, fundamento: iaSug?.fundamento || null },
  respuestaIA: ia ? JSON.stringify(ia) : '',
  reglas_aplicadas: ['R-CERT-0 certificado obligatorio', 'R-CERT-3 congruencia con el certificado', 'R-IDI-1 idioma', 'R-TAB-1 tabla presente',
                     'R-DOC-2 CC + proyecto por texto declarado', 'R-TAB-3 cambio no declarado', 'R-TAB-4 nota↔tabla (obs.)', 'R-RC-1 resumen clínico (obs.)',
                     'R-ROL-1 rol por contenido (obs.)', 'R-ROL-3 alcance no verificable (obs.)', 'R-ROL-4 duplicados (obs.)', 'R-TAB-2 declarado no encontrado (obs.)', 'R-CAL-1 rama calidad (obs.)']
};
if (debug) sal._textos = agregado.data;
return [{ json: sal }];
