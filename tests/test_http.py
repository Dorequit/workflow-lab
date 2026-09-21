"""Exercise the real local HTTP adapter on an ephemeral port."""

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from workflow_lab.server import Handler


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health_and_static_ui(self):
        with urlopen(self.url + "/api/health") as response:
            self.assertEqual(json.load(response)["status"], "ok")
        with urlopen(self.url + "/") as response:
            self.assertIn(b"Decisions you can", response.read())

    def test_end_to_end_run_and_reject_invalid_input(self):
        with urlopen(self.url + "/api/examples") as response:
            incident = json.load(response)[0]["incident"]
        request = Request(
            self.url + "/api/run",
            json.dumps(incident).encode(),
            {"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            self.assertEqual(json.load(response)["severity"], "SEV1")

        incident["affected_users"] = -1
        invalid = Request(
            self.url + "/api/run",
            json.dumps(incident).encode(),
            {"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(invalid)
        self.assertEqual(error.exception.code, 400)


if __name__ == "__main__":
    unittest.main()

