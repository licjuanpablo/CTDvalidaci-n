const items = $input.all();
const data = items.map(item => ({
  text: item.json.text || '',
  source: item.json.source || 'unknown',
  fileName: item.json.fileName || ''
}));
return [{ json: { data } }];
