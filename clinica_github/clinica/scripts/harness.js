// Corre reglas_clinicas.js localmente sobre textos capturados del flujo (sin IA). Uso: node harness.js <carpeta_captura> <carpeta_salida> [ia_dir]
const fs = require('fs'), path = require('path');
const [cap, outDir, iaDir] = process.argv.slice(2);
const code = fs.readFileSync(path.join(__dirname, '../workflow/nodos/reglas_clinicas.js'), 'utf8');
fs.mkdirSync(outDir, { recursive: true });
for (const f of fs.readdirSync(cap).filter(f => f.endsWith('.json'))) {
  const d = JSON.parse(fs.readFileSync(path.join(cap, f)));
  const data = d.textos || d._textos;
  let iaRaw = { skipped: true };
  const $ = n => ({
    all: () => n === 'Split archivos' ? [{ json: { expedienteForm: '' } }] : n === 'Code in JavaScript' ? [] : [{ json: { data } }],
    first: () => ({ json: n === 'Obtener todos los textos' ? { data } : {} }) });
  const $input = { first: () => ({ json: iaRaw }) };
  try {
    const r = new Function('$', '$input', code)($, $input);
    fs.writeFileSync(path.join(outDir, f), JSON.stringify(r[0].json, null, 1));
  } catch (e) { console.log(f, 'ERROR', e.stack.split('\n').slice(0, 3).join(' | ')); }
}
