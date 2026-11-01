// Valida a sintaxe das consultas M com o analisador oficial da Microsoft.
// Uso: python tests/coletar_m.py | node tests/validar_m.js
const pq = require('@microsoft/powerquery-parser');
let entrada = ''; process.stdin.on('data', d => entrada += d).on('end', async () => {
  const codigos = JSON.parse(entrada); let erros = 0;
  for (const [nome, codigo] of Object.entries(codigos)) {
    const r = await pq.TaskUtils.tryLexParse(pq.DefaultSettings, codigo);
    if (!pq.TaskUtils.isParseStageOk(r)) {
      erros++;
      const e = r.error; const msg = (e && (e.message || (e.innerError && e.innerError.message))) || String(e);
      console.log(`ERRO ${nome}: ${msg}`.slice(0, 300));
    }
  }
  console.log(`${Object.keys(codigos).length} consultas analisadas, ${erros} com erro`);
  process.exitCode = erros ? 1 : 0;
});
