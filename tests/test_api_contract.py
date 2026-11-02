"""Validate the existing API boundary in process, without providers or audio."""
import json
import socket
import subprocess
import unittest
from unittest.mock import patch
import httpx
from app.main import app


class APIContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://source-only.invalid')
        self.addAsyncCleanup(self.client.aclose)

    async def request(self, method, path, **kwargs):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')), patch.object(subprocess, 'Popen', side_effect=AssertionError('process execution forbidden')):
            return await self.client.request(method, path, **kwargs)

    async def test_health_is_readback_without_provider_or_process_effects(self):
        result = await self.request('GET', '/health')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {'status': 'ok', 'service': 'codestra-voice-agent'})

    async def test_provider_discovery_declares_only_existing_provider_identifiers(self):
        result = await self.request('GET', '/v1/providers')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {'tts': ['kokoro'], 'agents': ['pipecat', 'livekit'], 'mixxx': 'codestra-mixxx-native'})

    async def test_speech_defaults_preserve_the_existing_contract_without_audio_execution(self):
        result = await self.request('POST', '/v1/speech', json={'text': 'hello'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {'accepted': True, 'text': 'hello', 'voice': 'af_heart', 'language': 'en', 'provider': 'kokoro', 'status': 'QUEUED'})

    async def test_speech_preserves_explicit_unicode_and_literal_shell_text(self):
        payload = {'text': 'Hello 世界; $(touch forbidden)\nline two', 'voice': 'custom', 'language': 'fr'}
        result = await self.request('POST', '/v1/speech', json=payload)
        self.assertEqual(result.status_code, 200)
        for key, value in payload.items():
            self.assertEqual(result.json()[key], value)

    async def test_missing_null_and_wrong_type_fields_are_rejected(self):
        for payload in ({}, {'text': None}, {'text': []}, {'text': 'hello', 'voice': 12}, {'text': 'hello', 'language': {}}):
            with self.subTest(payload=payload):
                result = await self.request('POST', '/v1/speech', json=payload)
                self.assertEqual(result.status_code, 422)
                self.assertIn('detail', result.json())

    async def test_missing_malformed_and_non_json_bodies_are_rejected(self):
        for kwargs in ({}, {'content': '{', 'headers': {'Content-Type': 'application/json'}}, {'content': 'text', 'headers': {'Content-Type': 'text/plain'}}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual((await self.request('POST', '/v1/speech', **kwargs)).status_code, 422)

    async def test_undeclared_methods_and_paths_are_denied(self):
        for method, path, code in [('GET', '/v1/speech', 405), ('POST', '/health', 405), ('POST', '/v1/providers', 405), ('GET', '/unknown', 404)]:
            with self.subTest(method=method, path=path):
                self.assertEqual((await self.request(method, path)).status_code, code)

    async def test_generated_openapi_matches_the_actual_input_validation_surface(self):
        result = await self.request('GET', '/openapi.json')
        self.assertEqual(result.status_code, 200)
        contract = result.json()
        self.assertEqual(set(contract['paths']), {'/health', '/v1/providers', '/v1/speech'})
        self.assertEqual(set(contract['paths']['/v1/speech']), {'post'})
        speech = contract['components']['schemas']['Speech']
        self.assertEqual(speech['required'], ['text'])
        for field in ('text', 'voice', 'language'):
            self.assertEqual(speech['properties'][field]['type'], 'string')
        self.assertEqual(speech['properties']['voice']['default'], 'af_heart')
        self.assertEqual(speech['properties']['language']['default'], 'en')
        json.dumps(contract, allow_nan=False)

if __name__ == '__main__':
    unittest.main()
