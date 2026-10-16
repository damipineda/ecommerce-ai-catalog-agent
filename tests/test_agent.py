import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from pydantic import ValidationError

from agent import (
    AgentError, BusinessRules, ProductInput, cloud_chat, demo_draft,
    generate_catalog_payload, validate_draft,
)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.product = ProductInput(raw_product_input="mochila azul; 20 litros", customer_query="¿Es impermeable?")
        self.rules = BusinessRules(store_name="Demo", shipping_policy=None, warranty_policy=None)
        self.valid = demo_draft(self.product).model_dump_json()

    def test_demo_does_not_call_network(self):
        with patch("agent.cloud_chat") as chat:
            result = generate_catalog_payload(self.product, self.rules, demo=True)
        chat.assert_not_called()
        self.assertEqual(result["mode"], "demo")
        self.assertIsNone(result["model"])
        self.assertTrue(result["review_required"])

    def test_demo_depends_on_product(self):
        other = ProductInput(raw_product_input="termo rojo", customer_query="¿Color?")
        first = generate_catalog_payload(self.product, self.rules, demo=True)
        second = generate_catalog_payload(other, self.rules, demo=True)
        self.assertNotEqual(first["sku_id"], second["sku_id"])
        self.assertNotEqual(first["listing"], second["listing"])

    def test_rejects_invented_feature(self):
        data = json.loads(self.valid)
        data["bullet_features"] = ["acero inoxidable 304"]
        with self.assertRaises(ValueError):
            validate_draft(json.dumps(data), self.product)

    def test_enforces_seo_limit(self):
        data = json.loads(self.valid)
        data["seo_metadata"]["meta_title"] = "a" * 61
        with self.assertRaises(ValidationError):
            validate_draft(json.dumps(data), self.product)

    def test_rejects_empty_notes(self):
        with self.assertRaises(ValidationError):
            ProductInput(raw_product_input="  ", customer_query="Hola")

    def test_rejects_extra_fields(self):
        data = json.loads(self.valid)
        data["invented_field"] = "foo"
        with self.assertRaises(ValidationError):
            validate_draft(json.dumps(data), self.product)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_is_explicit(self):
        with patch("agent.cloud_chat") as chat, self.assertRaises(AgentError):
            generate_catalog_payload(self.product, self.rules)
        chat.assert_not_called()

    @patch.dict(os.environ, {"OLLAMA_API_KEY": "test-only"}, clear=True)
    def test_repairs_once(self):
        with patch("agent.cloud_chat", side_effect=["not json", self.valid]) as chat:
            result = generate_catalog_payload(self.product, self.rules)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(result["mode"], "ollama_cloud")

    @patch.dict(os.environ, {"OLLAMA_API_KEY": "test-only"}, clear=True)
    def test_failed_repair_does_not_return_demo(self):
        with patch("agent.cloud_chat", return_value="{}") as chat:
            with self.assertRaises(AgentError):
                generate_catalog_payload(self.product, self.rules)
        self.assertEqual(chat.call_count, 2)

    def test_cloud_request_uses_hosted_auth_and_no_structured_format(self):
        response = io.BytesIO(json.dumps({"message": {"content": self.valid}}).encode())
        with patch("agent.urlopen", return_value=response) as request:
            self.assertEqual(cloud_chat([], "test-only", "test-model"), self.valid)
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://ollama.com/api/chat")
        self.assertEqual(sent.get_header("Authorization"), "Bearer test-only")
        self.assertNotIn("format", json.loads(sent.data))
        self.assertFalse(json.loads(sent.data)["stream"])

    def test_provider_errors_do_not_expose_response_body(self):
        error = HTTPError("https://ollama.com/api/chat", 401, "sensitive-body", {}, None)
        with patch("agent.urlopen", side_effect=error):
            with self.assertRaises(AgentError) as caught:
                cloud_chat([], "test-only", "test-model")
        self.assertNotIn("sensitive-body", str(caught.exception))

    def test_connection_failure(self):
        with patch("agent.urlopen", side_effect=URLError("connection failed")):
            with self.assertRaises(AgentError):
                cloud_chat([], "test-only", "test-model")


if __name__ == "__main__":
    unittest.main()
