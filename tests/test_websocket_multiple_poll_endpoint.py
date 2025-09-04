import json

import pytest

from tests import assertion_helper
from tests.base import TestBase
from tests.helper import create_color_poll


class TestWebSocket(TestBase):

    def setup_method(self):
        self.poll = create_color_poll(self.client)

    def add_vote(self, poll_id: str, choice_id: str, username: str = "testuser"):
        payload = {"username": username, "choice_id": choice_id}
        res = self.client.post(f"/polls/{poll_id}/vote", json=payload)
        assert res.status_code == 200
        return res.json()

    def test_subscribe_unsubscribe_disconnect(self):
        poll_id = self.poll["id"]
        choice_id = self.poll["choices"][0]["id"]
        with self.client.websocket_connect("/polls/ws") as ws:
            assertion_helper.assert_successful_connect(ws.receive_text())
            # Try invalid poll
            ws.send_text(json.dumps({"action": "subscribe", "poll_id": "999"}))
            assertion_helper.assert_poll_not_found_error(ws.receive_text(), "999")

            # Try valid poll

            ws.send_text(json.dumps({"action": "subscribe", "poll_id": poll_id}))

            # Expect initial results

            assertion_helper.assert_successful_subscription(
                ws.receive_text(), poll_id, choice_id, 0
            )

            # Duplicate subscribe
            ws.send_text(json.dumps({"action": "subscribe", "poll_id": poll_id}))
            assertion_helper.assert_already_subscribed_error(ws.receive_text(), poll_id)

            # Unsubscribe
            ws.send_text(json.dumps({"action": "unsubscribe", "poll_id": poll_id}))
            assertion_helper.assert_successful_unsubscription(
                ws.receive_text(), poll_id
            )

            # Invalid unsubscribe
            ws.send_text(json.dumps({"action": "unsubscribe", "poll_id": poll_id}))
            assertion_helper.assert_not_subscribed_error(ws.receive_text(), poll_id)

            # Disconnect
            ws.send_text(json.dumps({"action": "disconnect"}))
            assertion_helper.assert_successful_disconnect(ws.receive_text())

            # After disconnect, connection should be closed
            with pytest.raises(Exception):
                ws.receive_text()

    def test_live_updates(self):
        poll_id = self.poll["id"]
        choice_id = self.poll["choices"][0]["id"]
        with self.client.websocket_connect("/polls/ws") as ws:
            assertion_helper.assert_successful_connect(ws.receive_text())
            ws.send_text(json.dumps({"action": "subscribe", "poll_id": poll_id}))
            assertion_helper.assert_successful_subscription(
                ws.receive_text(), poll_id, choice_id, 0
            )
            # Update the poll
            self.add_vote(poll_id, choice_id)
            # Expect a live update
            assertion_helper.assert_result_update(
                ws.receive_text(), poll_id, choice_id, 1
            )

    def test_live_updates_two_users(self):
        poll_id = self.poll["id"]
        choice_id = self.poll["choices"][0]["id"]
        with (
            self.client.websocket_connect("/polls/ws") as ws1,
            self.client.websocket_connect("/polls/ws") as ws2,
        ):
            assertion_helper.assert_successful_connect(ws1.receive_text())
            assertion_helper.assert_successful_connect(ws2.receive_text())
            ws1.send_text(json.dumps({"action": "subscribe", "poll_id": poll_id}))
            ws2.send_text(json.dumps({"action": "subscribe", "poll_id": poll_id}))
            # Expect initial results for both clients
            assertion_helper.assert_successful_subscription(
                ws1.receive_text(), poll_id, choice_id, 0
            )
            assertion_helper.assert_successful_subscription(
                ws2.receive_text(), poll_id, choice_id, 0
            )
            # Update the poll
            self.add_vote(poll_id, choice_id)
            # Expect a live update  for both clients
            assertion_helper.assert_result_update(
                ws1.receive_text(), poll_id, choice_id, 1
            )
            assertion_helper.assert_result_update(
                ws2.receive_text(), poll_id, choice_id, 1
            )
            # Disconnect one client
            assertion_helper.assert_successful_disconnect(
                ws1.send_text(json.dumps({"action": "disconnect"}))
                or ws1.receive_text()
            )
            assertion_helper.assert_successful_disconnect(
                ws2.send_text(json.dumps({"action": "disconnect"}))
                or ws2.receive_text()
            )

    def test_unknown_action(self):
        with self.client.websocket_connect("/polls/ws") as ws:
            assertion_helper.assert_successful_connect(ws.receive_text())
            ws.send_text(json.dumps({"action": "unknown_action"}))
            assertion_helper.assert_unknown_action_error(
                ws.receive_text(), "unknown_action"
            )
            # Disconnect
            ws.send_text(json.dumps({"action": "disconnect"}))
            assertion_helper.assert_successful_disconnect(ws.receive_text())
