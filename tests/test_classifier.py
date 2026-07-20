from classifier import DEFAULT_LABEL, EmailClassifier, format_label_definitions, parse_json_object


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

    invoice = classifier.classify("Factures", "billing@example.com", "Bonjour, voici votre facture numéro 123 en pièce jointe.")
    assert invoice["label"] == "À traiter"
    assert invoice["action"] == "keep"

    payment = classifier.classify("Veuillez mettre votre mode de paiement à jour", "billing@example.com", "Votre abonnement nécessite une action.")
    assert payment["label"] == "À traiter"
    assert payment["action"] == "keep"

    signed_document = classifier.classify("Vous êtes invité à signer des documents", "cabinet@example.com", "Bonjour, veuillez signer les documents.")
    assert signed_document["label"] == "À traiter"
    assert signed_document["action"] == "keep"

    notification = classifier.classify("Notification", "me@example.com", "Votre compte a été mis à jour.")
    assert notification["label"] == "Notification"
    assert notification["action"] == "keep"

    security = classifier.classify("Des informations de sécurité du compte Microsoft ont été ajoutées", "account@microsoft.com", "Compte Microsoft")
    assert security["label"] == "Notification"

    newsletter = classifier.classify("Newsletter", "me@example.com", "Découvrez nos nouveautés de la semaine.")
    assert newsletter["label"] == "Commercial"
    assert newsletter["action"] == "keep"

    digest = classifier.classify("Agent Hub Security + Evals - 2026-06-30", "news@example.com", "A paper-heavy window")
    assert digest["label"] == "Commercial"

    promo = classifier.classify("Invitez un proche sur Wise et obtenez 20 EUR", "wise@example.com", "Partagez les nouveautés")
    assert promo["label"] == "Commercial"

    uber = classifier.classify("De délicieuses offres vous attendent sur vos prochaines commandes", "Uber Eats", "Économisez sur vos plats favoris.")
    assert uber["label"] == "Commercial"

    product_hunt = classifier.classify("Bots with bank accounts", "Product Hunt Daily", "The fintech that's moved $3B is now letting AI agents spend money safely.")
    assert product_hunt["label"] == "Commercial"

    learning_rate = classifier.classify("Sonnet 5 + Agent Evals - 2026-07-01", "High Learning Rate", "A model-release-heavy window with practical lessons.")
    assert learning_rate["label"] == "Commercial"

    article = classifier.classify("25 ans auprès de Pierre Cardin", "Alec - Entrepreneur", "Ce qu'une légende de la mode m'a appris.")
    assert article["label"] == "Commercial"

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
    assert result["label"] == DEFAULT_LABEL
    assert result["action"] == "keep"
    assert result["priority"] == "low"
    assert result["confidence"] == 0.0
    assert result["reason"] == "Unclear"


def test_classifier_fallback():
    class Bad:
        class Chat:
            class Completions:
                def create(self, **kwargs):
                    raise RuntimeError("offline")

            completions = Completions()

        chat = Chat()

    result = EmailClassifier("", client=Bad()).safe_classify("", "", "")
    assert result["label"] == DEFAULT_LABEL
    assert result["action"] == "keep"


def test_prompt_definitions_include_label_meaning():
    text = format_label_definitions(
        {
            "À traiter": {"description": "Factures et documents", "action_hint": "keep", "examples": ["Facture"]},
            "Commentaire": {"description": "Vraies mentions", "action_hint": "keep", "examples": ["Mention"]},
        }
    )
    assert "Factures et documents" in text
