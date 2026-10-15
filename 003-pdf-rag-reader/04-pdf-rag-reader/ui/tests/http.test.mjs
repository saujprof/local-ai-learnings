import assert from 'node:assert/strict'
import { test } from 'node:test'
import { AxiosError } from 'axios'
import { createHttpClient, ApiError } from '../src/services/http.ts'

function response(config, data, status = 200) {
  return { config, data, status, statusText: '', headers: {} }
}

test('JSON and empty 204 responses; configured timeout', async () => {
  const client = createHttpClient('/api')
  assert.equal(client.defaults.timeout, 300000)
  client.defaults.adapter = async config => response(config, { status: 'ok' })
  assert.deepEqual((await client.get('/health')).data, { status: 'ok' })
  client.defaults.adapter = async config => response(config, '', 204)
  assert.equal((await client.delete('/docs/one')).status, 204)
})

test('backend error envelope retains code, status, and message', async () => {
  const client = createHttpClient()
  client.defaults.adapter = async config => {
    throw new AxiosError('error', 'ERR_BAD_REQUEST', config, null,
      response(config, { error: { code: 'chat_busy', message: 'Chat is busy.' } }, 409))
  }
  await assert.rejects(client.post('/chat'), error =>
    error instanceof ApiError && error.status === 409 && error.code === 'chat_busy' && error.message === 'Chat is busy.')
})

test('network failure does not retry and marks mutations ambiguous', async () => {
  const client = createHttpClient()
  let calls = 0
  client.defaults.adapter = async config => {
    calls++
    throw new AxiosError('offline', 'ERR_NETWORK', config)
  }
  await assert.rejects(client.post('/chat'), error => error.ambiguous && error.code === 'network_error')
  assert.equal(calls, 1)
  await assert.rejects(client.get('/docs'), error => !error.ambiguous)
})

test('timeouts and non-JSON failures have useful fallbacks', async () => {
  const client = createHttpClient()
  client.defaults.adapter = async config => { throw new AxiosError('timeout', 'ECONNABORTED', config) }
  await assert.rejects(client.delete('/docs/one'), error => error.ambiguous && error.code === 'request_timeout')
  client.defaults.adapter = async config => { throw new AxiosError('error', 'ERR_BAD_RESPONSE', config, null, response(config, '<html>error</html>', 502)) }
  await assert.rejects(client.get('/docs'), error => error.status === 502 && !error.message.includes('<html>'))
})
