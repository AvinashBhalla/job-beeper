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

    def test_semantically_invalid_first_result_falls_back(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,openrouter",
            "GROQ_API_KEY": "groq-key",
            "GROQ_MODEL": "groq-model",
            "OPENROUTER_API_KEY": "router-key",
            "OPENROUTER_MODEL": "router-model",
        }, clear=True):
            invalid = self.response(200, {"choices": [{"message": {"content": '{"ok": "not-a-boolean"}'}}]})
            valid = self.response(200, {"choices": [{"message": {"content": '{"ok": true}'}}]})
            with patch.object(llm_router.requests, "post", side_effect=[invalid, valid]) as post:
                result, provider_name = llm_router.generate_with_fallback(
                    "Extract: ", self.job_data, self.schema,
                    validator=lambda payload: (
                        payload if isinstance(payload.get("ok"), bool)
                        else (_ for _ in ()).throw(ValueError("invalid_result_shape"))
                    ),
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


    def test_native_gemini_request_and_response(self):
        provider = llm_router.ProviderConfig("gemini", "gemini-test-key", "gemini-test-model")
        mock = self.response(200, {
            "candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]
        })
        with patch.object(llm_router.requests, "post", return_value=mock) as post:
            result = llm_router.generate_json(
                provider, "Extract carefully: ", self.job_data, self.schema
            )
        self.assertEqual(result, {"ok": True})
        args, kwargs = post.call_args
        self.assertEqual(
            args[0],
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-test-model:generateContent",
        )
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "gemini-test-key")
        self.assertEqual(kwargs["json"]["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(kwargs["json"]["generationConfig"]["responseSchema"], self.schema)
        self.assertEqual(kwargs["timeout"], (5, 20))

    def test_openrouter_request_and_response(self):
        provider = llm_router.ProviderConfig("openrouter", "router-test-key", "router-test-model")
        mock = self.response(200, {
            "choices": [{"message": {"content": '{"ok": true}'}}]
        })
        with patch.object(llm_router.requests, "post", return_value=mock) as post:
            result = llm_router.generate_json(
                provider, "Extract carefully: ", self.job_data, self.schema
            )
        self.assertEqual(result, {"ok": True})
        args, kwargs = post.call_args
        self.assertEqual(args[0], llm_router.PROVIDER_ENDPOINTS["openrouter"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer router-test-key")
        self.assertEqual(kwargs["json"]["model"], "router-test-model")
        self.assertEqual(kwargs["json"]["response_format"], {"type": "json_object"})

    def test_nvidia_request_and_response(self):
        provider = llm_router.ProviderConfig("nvidia", "nvidia-test-key", "nvidia-test-model")
        mock = self.response(200, {
            "choices": [{"message": {"content": '{"ok": true}'}}]
        })
        with patch.object(llm_router.requests, "post", return_value=mock) as post:
            result = llm_router.generate_json(
                provider, "Extract carefully: ", self.job_data, self.schema
            )
        self.assertEqual(result, {"ok": True})
        args, kwargs = post.call_args
        self.assertEqual(args[0], llm_router.PROVIDER_ENDPOINTS["nvidia"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer nvidia-test-key")
        self.assertEqual(kwargs["json"]["model"], "nvidia-test-model")
        self.assertEqual(kwargs["json"]["response_format"], {"type": "json_object"})

    def test_malformed_empty_and_missing_model_content_are_sanitized(self):
        provider = llm_router.ProviderConfig("openrouter", "router-test-key", "router-test-model")
        payloads = [
            {"choices": [{"message": {"content": "not-json-private-response"}}]},
            {"choices": [{"message": {"content": ""}}]},
            {"choices": [{"message": {"content": None}}]},
            {"choices": []},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with patch.object(
                    llm_router.requests, "post", return_value=self.response(200, payload)
                ):
                    with self.assertRaises(llm_router.ProviderRequestError) as caught:
                        llm_router.generate_json(
                            provider, "Extract: ", self.job_data, self.schema
                        )
                self.assertEqual(caught.exception.code, "invalid_model_json")
                self.assertNotIn("private-response", str(caught.exception))

    def test_http_5xx_falls_back_to_next_provider_without_body_leak(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,openrouter",
            "GROQ_API_KEY": "groq-key",
            "GROQ_MODEL": "groq-model",
            "OPENROUTER_API_KEY": "router-key",
            "OPENROUTER_MODEL": "router-model",
        }, clear=True):
            failed = self.response(503, {"error": {"message": "HTTP_BODY_PRIVATE"}})
            success = self.response(200, {"choices": [{"message": {"content": '{"ok": true}'}}]})
            with self.assertLogs("job-radar.llm-router", level="WARNING") as logs:
                with patch.object(
                    llm_router.requests, "post", side_effect=[failed, success]
                ) as post:
                    result, provider_name = llm_router.generate_with_fallback(
                        "Extract: ", self.job_data, self.schema
                    )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(provider_name, "openrouter")
        self.assertEqual(post.call_count, 2)
        self.assertNotIn("HTTP_BODY_PRIVATE", "\n".join(logs.output))

    def test_connection_error_falls_back_without_logging_exception_text(self):
        private_text = "JOB_DESCRIPTION_PRIVATE EVIDENCE_PRIVATE CONNECTION_PRIVATE"
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,openrouter",
            "GROQ_API_KEY": "groq-key",
            "GROQ_MODEL": "groq-model",
            "OPENROUTER_API_KEY": "router-key",
            "OPENROUTER_MODEL": "router-model",
        }, clear=True):
            success = self.response(200, {"choices": [{"message": {"content": '{"ok": true}'}}]})
            with self.assertLogs("job-radar.llm-router", level="WARNING") as logs:
                with patch.object(
                    llm_router.requests, "post",
                    side_effect=[requests.ConnectionError(private_text), success],
                ) as post:
                    result, provider_name = llm_router.generate_with_fallback(
                        "Extract: ", self.job_data, self.schema
                    )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(provider_name, "openrouter")
        self.assertEqual(post.call_count, 2)
        rendered_logs = "\n".join(logs.output)
        for secret in ("JOB_DESCRIPTION_PRIVATE", "EVIDENCE_PRIVATE", "CONNECTION_PRIVATE"):
            self.assertNotIn(secret, rendered_logs)

    def test_validator_exception_text_is_allowlisted_before_logging(self):
        private_text = "EVIDENCE_PRIVATE JOB_DESCRIPTION_PRIVATE"
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,openrouter",
            "GROQ_API_KEY": "groq-key",
            "GROQ_MODEL": "groq-model",
            "OPENROUTER_API_KEY": "router-key",
            "OPENROUTER_MODEL": "router-model",
        }, clear=True):
            invalid = self.response(200, {"choices": [{"message": {"content": '{"ok": false}'}}]})
            success = self.response(200, {"choices": [{"message": {"content": '{"ok": true}'}}]})

            def validator(payload):
                if payload.get("ok") is not True:
                    raise ValueError("invalid_payload " + private_text)
                return payload

            with self.assertLogs("job-radar.llm-router", level="WARNING") as logs:
                with patch.object(
                    llm_router.requests, "post", side_effect=[invalid, success]
                ) as post:
                    result, provider_name = llm_router.generate_with_fallback(
                        "Extract: ", self.job_data, self.schema, validator=validator
                    )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(provider_name, "openrouter")
        self.assertEqual(post.call_count, 2)
        rendered_logs = "\n".join(logs.output)
        self.assertIn("code=invalid_result", rendered_logs)
        self.assertNotIn("invalid_payload", rendered_logs)
        self.assertNotIn("EVIDENCE_PRIVATE", rendered_logs)
        self.assertNotIn("JOB_DESCRIPTION_PRIVATE", rendered_logs)

    def test_all_provider_failures_are_exhausted_and_sanitized(self):
        secrets = ("KEY_PRIVATE", "MODEL_RESPONSE_PRIVATE", "JOB_DESCRIPTION_PRIVATE", "EVIDENCE_PRIVATE")
        with patch.dict(os.environ, {
            "LLM_PROVIDER_ORDER": "groq,gemini,openrouter,nvidia",
            "GROQ_API_KEY": "KEY_PRIVATE",
            "GROQ_MODEL": "groq-test-model",
            "GEMINI_API_KEY": "gemini-key",
            "GEMINI_MODEL": "gemini-test-model",
            "OPENROUTER_API_KEY": "router-key",
            "OPENROUTER_MODEL": "router-test-model",
            "NVIDIA_API_KEY": "nvidia-key",
            "NVIDIA_MODEL": "nvidia-test-model",
        }, clear=True):
            failures = [
                self.response(429, {"error": {"message": "MODEL_RESPONSE_PRIVATE"}}),
                self.response(503, {"error": {"message": "MODEL_RESPONSE_PRIVATE"}}),
                requests.ConnectionError("JOB_DESCRIPTION_PRIVATE EVIDENCE_PRIVATE"),
                self.response(502, {"error": {"message": "MODEL_RESPONSE_PRIVATE"}}),
            ]
            with self.assertLogs("job-radar.llm-router", level="WARNING") as logs:
                with patch.object(
                    llm_router.requests, "post", side_effect=failures
                ) as post:
                    with self.assertRaisesRegex(RuntimeError, "llm_all_providers_failed") as caught:
                        llm_router.generate_with_fallback(
                            "Extract: ", self.job_data, self.schema
                        )
        self.assertEqual(post.call_count, 4)
        error_text = str(caught.exception)
        for secret in secrets:
            self.assertNotIn(secret, error_text)
            self.assertNotIn(secret, "\n".join(logs.output))
        self.assertIn("groq:http_429", error_text)
        self.assertIn("gemini:http_503", error_text)
        self.assertIn("openrouter:request_failed", error_text)
        self.assertIn("nvidia:http_502", error_text)


if __name__ == "__main__":
    unittest.main()
