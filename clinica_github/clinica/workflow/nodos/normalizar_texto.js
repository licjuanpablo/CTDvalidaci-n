// Normaliza la salida del extractor (PDF digital) o del OCR de Gemini y conserva el nombre del archivo.
const item = $input.first();
let fileName = '';
try { fileName = $('Code in JavaScript').first().json.filename || ''; } catch (e) {}
if (item.json.candidates) {
  const texto = item.json.candidates
    .map(c => (c.content?.parts || []).filter(p => !p.thought).map(p => p.text || '').join('') || '')
    .join('\n\n');
  return [{ json: { text: texto, source: 'gemini_ocr', fileName } }];
}
if (item.json.text) {
  return [{ json: { text: item.json.text, source: 'digital', fileName, numpages: item.json.numpages || null } }];
}
return [{ json: { text: '', source: 'unknown', fileName } }];
