from classifier import EmailClassifier, parse_json_object


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
    result = EmailClassifier("", client=Client()).classify("Demo", "lead@example.com", "Random note")
    assert result["label"] == "À répondre"
    assert result["action"] == "draft"
    assert result["priority"] == "high"
    assert result["confidence"] == 0.92
    assert result["reason"] == "Sender expects a reply"


def test_parse_json_object_from_markdown():
    result = parse_json_object('```json\n{"label":"Commentaire","action":"keep"}\n```')
    assert result["label"] == "Commentaire"


def test_deterministic_gmail_examples():
    classifier = EmailClassifier("", client=Client())

    notification = classifier.classify("Notification", "me@example.com", "Votre compte a été mis à jour.")
    assert notification["label"] == "Notification"
    assert notification["action"] == "mark_read"

    newsletter = classifier.classify("Newsletter", "me@example.com", "Découvrez nos nouveautés de la semaine.")
    assert newsletter["label"] == "Newsletter"
    assert newsletter["action"] == "trash"

    reply = classifier.classify("Demande de reponse", "me@example.com", "Bonjour, pouvez-vous me rappeler pour discuter de votre offre ?")
    assert reply["label"] == "À répondre"
    assert reply["action"] == "draft"


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
