import hashlib
import hmac
import io
import time
import unittest
from unittest.mock import patch

from flask import Flask

from config import TestingConfig
from modules.box__linkolearn.slack.view import module_blueprint


class TestSlackRequestBodyLimit(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.register_blueprint(module_blueprint)
        self.client = self.app.test_client()
        self.limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.secret = "test-slack-signing-secret"
        signing_secret = patch.dict("os.environ", SLACK_SIGNING_SECRET=self.secret)
        signing_secret.start()
        self.addCleanup(signing_secret.stop)

    def signed_headers(self, body):
        timestamp = str(int(time.time()))
        signature = hmac.new(
            self.secret.encode(),
            b"v0:" + timestamp.encode() + b":" + body,
            hashlib.sha256,
        ).hexdigest()
        return {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": "v0=" + signature,
        }

    def test_oversized_body_is_rejected_before_reading(self):
        body = b"x" * (self.limit + 1)
        for route in ("payload", "options"):
            with self.subTest(route=route):
                stream = io.BytesIO(body)
                response = self.client.post(
                    f"/slack/{route}",
                    input_stream=stream,
                    content_length=len(body),
                    headers=self.signed_headers(body),
                )
                self.assertEqual(response.status_code, 413)
                self.assertEqual(stream.tell(), 0)

    def test_oversized_stream_without_content_length_is_bounded(self):
        body = b"x" * (self.limit + 1)
        for route in ("payload", "options"):
            with self.subTest(route=route):
                stream = io.BytesIO(body)
                response = self.client.post(
                    f"/slack/{route}",
                    headers=self.signed_headers(body),
                    environ_overrides={
                        "wsgi.input": stream,
                        "wsgi.input_terminated": True,
                        "CONTENT_LENGTH": "",
                    },
                )
                # Werkzeug 2.3 caps unknown-length streams; the truncated body
                # must fail verification against the full request signature.
                self.assertEqual(response.status_code, 401)
                self.assertEqual(stream.tell(), self.limit)

    def test_signed_forms_below_and_at_limit_reach_route_handling(self):
        for route, form, status, result in (
            ("payload", b"padding=", 400, {"error": "No payload"}),
            ("options", b"payload=%7B%7D&padding=", 200, {"options": []}),
        ):
            for size in (len(form), self.limit):
                with self.subTest(route=route, size=size):
                    body = form + b"x" * (size - len(form))
                    response = self.client.post(
                        f"/slack/{route}",
                        data=body,
                        content_type="application/x-www-form-urlencoded",
                        headers=self.signed_headers(body),
                    )
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(response.get_json(), result)

    def test_invalid_signatures_are_still_rejected(self):
        body = b"payload=%7B%7D"
        headers = self.signed_headers(body)
        headers["X-Slack-Signature"] = "v0=" + "0" * 64
        for route in ("payload", "options"):
            with self.subTest(route=route):
                response = self.client.post(
                    f"/slack/{route}", data=body, headers=headers
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.get_json(), {"error": "invalid request signature"}
                )
