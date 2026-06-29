import json
import logging

from json_logging import JsonFormatter


def test_json_log_contains_required_email_fields():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "email_classified", (), None)
    record.event = "email_classified"
    record.client_id = "exuvie"
    record.connector = "gmail"
    record.account = "main"
    record.message_id = "m1"
    record.label = "Client"
    record.action = "draft"
    record.priority = "high"
    record.status = "ok"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "email_classified"
    assert payload["client_id"] == "exuvie"
    assert payload["connector"] == "gmail"
    assert payload["account"] == "main"
    assert payload["message_id"] == "m1"
    assert payload["priority"] == "high"
