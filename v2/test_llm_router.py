import json
import os
import unittest
from unittest.mock import patch

import requests

from v2 import llm_router


class LLMRouterConfigurationTests(unittest.TestCase):
    def test_only_providers_with_key_and_model_are_configured(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,gemini,openrouter,nvidia,unknown,groq",
            "GROQ_API_KEY": "groq-secret",
            "GROQ_MODEL": "groq-test-model",
            "GEMINI_API_KEY": "gemini-secret",
            "GEMINI_MODEL": "gemini-test-model",
            "OPENROUTER_API_KEY": "router-secret",
            "OPENROUTER_MODEL": "",
            "NVIDIA_API_KEY": "",
            "NVIDIA_MODEL": "nvidia-test-model",
        }, clear=True):
            providers = llm_router.configured_providers()
        self.assertEqual([(p.name, p.model) for p in providers], [
            ("groq", "groq-test-model"), ("gemini", "gemini-test-model")
        ])

    def test_cache_identity_does_not_include_api_keys(self):
        with patch.dict(os.environ, {
            "LLM_ROUTER_ENABLED": "true",
            "LLM_PROVIDER_ORDER": "groq,gemini",
            "GROQ_API_KEY": "do-not-leak-this",
            "GROQ_MODEL": "groq-test-model",
            "GEMINI_API_KEY": "also-secret",
            "GEMINI_MODEL": "gemini-test-model",
        }, clear=True):
            identity = llm_router.cache_model_identity()
        self.assertIn("groq:groq-test-model", identity)
        self.assertIn("gemini:gemini-test-model", identity)
        self.assertNotIn("do-not-leak-this", identity)
        self.assertNotIn("also-secret", identity)

    def test_disabled_router_preserves_legacy_gemini_model_identity(self):
        with patch.dict(os.environ, {
            "LLM_ROUTER_ENABLED": "false",
            "GEMINI_MODEL": "gemini-legacy-model",
        }, clear=True):
            self.assertEqual(llm_router.cache_model_identity(), "gemini-legacy-model")


class LLMRouterRequestTests(unittest.TestCase):
    def setUp(self):
        self.schema = {"type": "OBJECT", "properties": {"ok": {"type": "BOOLEAN"}}}
        self.job_data = {"title": "Example Engineer", "description": "untrusted job text"}

    @staticmethod
    def response(status, payload):
        class Response:
            status_code = status
            def json(self):
                return payload
        return Response()

    def test_groq_openai_compatible_request_parses_json(self):
        provider = llm_router.ProviderConfig("groq", "test-key", "test-model")
        mock = self.response(200, {"choices": [{"message": {"content": json.dumps({"ok": True})}}]})
        with patch.object(llm_router.requests, "post", return_value=mock) as post:
            result = llm_router.generate_json(provider, "Extract carefully: ", self.job_data, self.schema)
        self.assertEqual(result, {"ok": True})
        args, kwargs = post.call_args
        self.assertEqual(args[0], llm_router.PROVIDER_ENDPOINTS["groq"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "test-model")
        self.assertEqual(kwargs["json"]["response_format"], {"type": "json_object"})
        self.assertEqual(kwargs["timeout"], (5, 20))

    def test_fallback_uses_next_provider_after_rate_limit(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,openrouter",
            "GROQ_API_KEY": "groq-key",
            "GROQ_MODEL": "groq-model",
            "OPENROUTER_API_KEY": "router-key",
            "OPENROUTER_MODEL": "router-model",
        }, clear=True):
            rate_limited = self.response(429, {"error": {"message": "private response details"}})
            success = self.response(200, {"choices": [{"message": {"content": '{"ok": true}'}}]})
            with patch.object(llm_router.requests, "post", side_effect=[rate_limited, success]) as post:
                result, provider_name = llm_router.generate_with_fallback(
                    "Extract: ", self.job_data, self.schema
                )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(provider_name, "openrouter")
        self.assertEqual(post.call_count, 2)

    def test_failure_does_not_expose_response_body_or_key(self):
        provider = llm_router.ProviderConfig("groq", "super-secret", "test-model")
        response = self.response(401, {"error": {"message": "response-body-secret"}})
        with patch.object(llm_router.requests, "post", return_value=response):
            with self.assertRaises(llm_router.ProviderRequestError) as caught:
                llm_router.generate_json(provider, "Extract: ", self.job_data, self.schema)
        message = str(caught.exception)
        self.assertIn("groq_http_401", message)
        self.assertNotIn("super-secret", message)
        self.assertNotIn("response-body-secret", message)

    def test_network_timeout_is_available_for_router_fallback(self):
        provider = llm_router.ProviderConfig("groq", "test-key", "test-model")
        with patch.object(llm_router.requests, "post", side_effect=requests.Timeout()):
            with self.assertRaises(requests.Timeout):
                llm_router.generate_json(provider, "Extract: ", self.job_data, self.schema)


if __name__ == "__main__":
    unittest.main()
