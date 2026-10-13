import Fastify from 'fastify';
import Redis from 'ioredis';

const PORT = Number(process.env.PORT ?? 8080);
const REDIS_URL = process.env.REDIS_URL ?? 'redis://localhost:6379';
const KEY = 'benchmark:data';

const redis = new Redis(REDIS_URL);
const app = Fastify();

app.get('/data', async (_req, reply) => {
  const data = await redis.get(KEY);
  if (data === null) return reply.code(404).send({ error: 'key not set, run scripts/setup.py' });
  return reply.type('application/json').send(data);
});

await app.listen({ port: PORT, host: '0.0.0.0' });
