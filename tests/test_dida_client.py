import base64
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

from dida_hotel_audit.dida_client import DidaClient


class _FakeDidaHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        expected = "Basic " + base64.b64encode(b"fake-client:fake-license").decode("ascii")
        if self.path != "/api/v1/hotel/details" or self.headers.get("Authorization") != expected:
            self.send_response(401)
            self.end_headers()
            return
        body = gzip.compress(
            json.dumps(
                {
                    "traceId": "synthetic-trace",
                    "timestamp": "123",
                    "data": [{"id": item, "name": f"Hotel {item}"} for item in payload["hotelIds"]],
                }
            ).encode("utf-8")
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class DidaClientTests(unittest.TestCase):
    def test_hotel_details_post_and_gzip(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeDidaHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            client = DidaClient(
                "fake-client", "fake-license", base_url=f"http://{host}:{port}"
            )
            result = client.hotel_details([101, 202])
            self.assertEqual(result["traceId"], "synthetic-trace")
            self.assertEqual([item["id"] for item in result["data"]], [101, 202])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
