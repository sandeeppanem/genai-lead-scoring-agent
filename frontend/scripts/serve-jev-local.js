const fs = require('fs');
const http = require('http');
const path = require('path');
const handler = require('../api/jev');

const loadLocalEnv = () => {
  const envPath = path.join(__dirname, '..', '.env.local');
  if (!fs.existsSync(envPath)) return;
  fs.readFileSync(envPath, 'utf8').split(/\r?\n/).forEach((line) => {
    const match = line.match(/^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match || process.env[match[1]]) return;
    process.env[match[1]] = match[2].replace(/^['"]|['"]$/g, '');
  });
};

loadLocalEnv();
process.env.JEV_ADAPTER_TOKEN = process.env.JEV_ADAPTER_TOKEN || 'local-dev-only';
const port = Number(process.env.JEV_LOCAL_PORT || 3001);

const server = http.createServer((request, response) => {
  if (request.url.split('?')[0] !== '/api/jev') {
    response.writeHead(404, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ error: 'Not found' }));
    return;
  }
  const chunks = [];
  let size = 0;
  request.on('data', (chunk) => {
    size += chunk.length;
    if (size <= 100000) chunks.push(chunk);
  });
  request.on('end', async () => {
    const body = Buffer.concat(chunks).toString('utf8');
    const adapterRequest = {
      method: request.method,
      headers: request.headers,
      body,
    };
    const adapterResponse = {
      statusCode: 200,
      headers: {},
      setHeader(name, value) { this.headers[name] = value; },
      status(code) { this.statusCode = code; return this; },
      json(payload) {
        response.writeHead(this.statusCode, { 'Content-Type': 'application/json', ...this.headers });
        response.end(JSON.stringify(payload));
      },
    };
    try {
      await handler(adapterRequest, adapterResponse);
    } catch (error) {
      response.writeHead(502, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ error: 'Local adapter failed' }));
    }
  });
});

server.listen(port, '127.0.0.1', () => {
  console.log(`Local Jev adapter listening on http://127.0.0.1:${port}/api/jev`);
});
