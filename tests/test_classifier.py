import pytest

from classifier import DEFAULT_LABEL, EmailClassifier, LABELS, format_label_definitions, normalize_model_result, parse_json_object


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
    result = parse_json_object('```json\n{"label":"À lire","action":"keep"}\n```')
    assert result["label"] == "À lire"


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

    commercial_update = classifier.classify("Offre commerciale", "me@example.com", "Découvrez nos nouveautés de la semaine.")
    assert commercial_update["label"] == "Commercial"
    assert commercial_update["action"] == "keep"

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


    job_alert = classifier.classify("QUALIBAT recherche un/e D\u00e9veloppeur Data & IA H/F + 8 nouvelles offres", "Indeed", "")
    assert job_alert["label"] == "Commercial"

    linkedin_job = classifier.classify("Alternance - Data Engineer chez Numberly", "Alertes LinkedIn Jobs", "")
    assert linkedin_job["label"] == "Commercial"

    free_shipping = classifier.classify("\u00c0 vous de jouer", "boohooMAN", "Livraison gratuite d\u00e8s 10 EUR. Se d\u00e9sabonner")
    assert free_shipping["label"] == "Commercial"

    software_discount = classifier.classify("Arr\u00eate de louer ton logiciel", "Emergent", "Jusqu\u0027\u00e0 95% de r\u00e9duction sur Standard.")
    assert software_discount["label"] == "Commercial"

    personal_question = classifier.classify("Question sur InboxPilot", "Ilyesse El Adaoui", "Est-ce que tu peux me dire si tu as eu le temps de regarder les derniers tests ?")
    assert personal_question["label"] == "\u00c0 r\u00e9pondre"
    assert personal_question["action"] == "draft"


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
            "À lire": {"description": "Vraies mentions", "action_hint": "keep", "examples": ["Mention"]},
        }
    )
    assert "Factures et documents" in text


def test_unknown_label_falls_back_to_default_label():
    result = normalize_model_result({"label": "Label non autorisé", "action": "keep", "priority": "medium", "confidence": 0.9}, LABELS)
    assert result["label"] == DEFAULT_LABEL
