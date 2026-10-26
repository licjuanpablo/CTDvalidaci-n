const item = $input.first();
const binaryKeys = Object.keys(item.binary || {});
const b = item.json.body || {};
// Campos del formulario web: expediente (texto), sin_ia=1 (no llama a Gemini; solo reglas), debug=1 (devuelve textos)
const expedienteForm = item.json.expediente || b.expediente || '';
const sinIA = String(item.json.sin_ia || b.sin_ia || '') === '1';
const debug = String(item.json.debug || b.debug || '') === '1';
return binaryKeys.map(key => ({
  json: { filename: item.binary[key].fileName, expedienteForm, sinIA, debug },
  binary: { data: item.binary[key] }
}));
