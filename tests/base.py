from fastapi.testclient import TestClient

from polling_app.main import app


class TestBase:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)
