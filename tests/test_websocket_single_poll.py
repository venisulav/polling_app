from tests import assertion_helper
from tests.base import TestBase
from tests.helper import create_color_poll, create_lunch_poll


class TestWebSocket(TestBase):

    def setup_method(self):
        self.poll = create_lunch_poll(self.client)

    def add_vote(self, poll_id: str, choice_id: str, username: str = "testuser"):
        payload = {"username": username, "choice_id": choice_id}
        res = self.client.post(f"/polls/{poll_id}/vote", json=payload)
        assert res.status_code == 200
        return res.json()

    def test_live_updates(
        self,
    ):
        poll = create_color_poll(self.client)
        poll_id = poll["id"]
        choice_id = poll["choices"][0]["id"]
        with self.client.websocket_connect(f"/polls/ws/{poll_id}") as ws:
            assertion_helper.assert_successful_connect(ws.receive_text())
            # Expect initial results
            assertion_helper.assert_successful_subscription(
                ws.receive_text(), poll_id, choice_id, 0
            )
            # Update the poll
            self.add_vote(poll_id, choice_id)
            # Expect a live update
            assertion_helper.assert_result_update(
                ws.receive_text(), poll_id, choice_id, 1
            )

    def test_with_non_existent_poll_id(self):
        with self.client.websocket_connect("/polls/ws/999") as ws:
            assertion_helper.assert_successful_connect(ws.receive_text())
            assertion_helper.assert_poll_not_found_error(ws.receive_text(), "999")

    def test_with_deleted_poll(self):
        poll_id = self.poll["id"]
        choice_id = self.poll["choices"][0]["id"]
        with self.client.websocket_connect(f"/polls/ws/{poll_id}") as ws:
            assertion_helper.assert_successful_connect(ws.receive_text())
            # Expect initial results
            assertion_helper.assert_successful_subscription(
                ws.receive_text(), poll_id, choice_id, 0
            )
            # Delete the poll
            res = self.client.delete(f"/polls/{poll_id}")
            assert res.status_code == 200
            assert res.json()["status"] == "deleted"
            # Expect a poll deleted error
            assertion_helper.assert_poll_deleted_error(ws.receive_text(), poll_id)
