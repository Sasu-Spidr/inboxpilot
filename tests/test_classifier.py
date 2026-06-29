from classifier import EmailClassifier


class Response:
    class Choice:
        class Message:
            content = '{"label":"À répondre","action":"draft","priority":"high","confidence":0.92,"reason":"Sender expects a reply"}'

        message = Message()

    choices = [Choice()]


class Chat:
    class Completions:
        def create(self, **kwargs):
            return Response()

    completions = Completions()


class Client:
    chat = Chat()


def test_classification():
    result = EmailClassifier("", client=Client()).classify("Demo", "lead@example.com", "Can we talk?")
    assert result["label"] == "À répondre"
    assert result["action"] == "draft"
    assert result["priority"] == "high"
    assert result["confidence"] == 0.92
    assert result["reason"] == "Sender expects a reply"


def test_low_confidence_goes_to_manual_review():
    class LowResponse:
        class Choice:
            class Message:
                content = '{"label":"À répondre","action":"draft","priority":"high","confidence":0.5,"reason":"Unclear"}'

            message = Message()

        choices = [Choice()]

    class LowClient:
        class Chat:
            class Completions:
                def create(self, **kwargs):
                    return LowResponse()

            completions = Completions()

        chat = Chat()

    result = EmailClassifier("", client=LowClient()).classify("Demo", "lead@example.com", "Maybe")
    assert result == {"label": "Commentaire", "action": "keep", "priority": "medium", "confidence": 0.0, "reason": "Unclear"}


def test_classifier_fallback():
    class Bad:
        class Chat:
            class Completions:
                def create(self, **kwargs):
                    raise RuntimeError("offline")

            completions = Completions()

        chat = Chat()

    result = EmailClassifier("", client=Bad()).safe_classify("", "", "")
    assert result["label"] == "Commentaire"
    assert result["action"] == "keep"
