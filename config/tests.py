import json

from django.test import SimpleTestCase


class ApiContractTests(SimpleTestCase):
    def test_swagger_json_documents_current_contracts(self):
        response = self.client.get("/api/swagger.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        schema = json.loads(response.content)

        upload = schema["paths"]["/knowledge/bases/{kb_id}/documents/"]["post"]
        upload_fields = {parameter["name"] for parameter in upload["parameters"]}
        self.assertTrue({"title", "source_type", "file", "source_url"} <= upload_fields)

        message = schema["paths"]["/chat/sessions/{session_id}/messages/"]["post"]
        self.assertEqual(message["parameters"][0]["schema"]["$ref"], "#/definitions/CreateMessage")
        self.assertIn("201", message["responses"])

        dashboard = schema["paths"]["/accounts/dashboard-summary/"]["get"]
        dashboard_fields = dashboard["responses"]["200"]["schema"]["properties"]
        self.assertIn("total_documents", dashboard_fields)

        refresh = schema["paths"]["/auth/token/refresh/"]["post"]["responses"]
        self.assertIn("200", refresh)
        self.assertNotIn("201", refresh)
        self.assertEqual(
            set(refresh["200"]["schema"]["properties"]),
            {"access", "refresh"},
        )

    def test_unknown_api_path_returns_json_error(self):
        response = self.client.get(
            "/api/knowledge/bases/not-a-uuid/documents/"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["status"], "error")
