from draft_generator import DraftGenerator

class Client:
    class Chat:
        class Completions:
            def create(self, **kwargs):
                return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "Bonjour, merci pour votre message."})()})()]})()
        completions = Completions()
    chat = Chat()

def test_draft_generation():
    assert DraftGenerator("", client=Client()).generate("Bonjour", "a@b.com", "Bonjour").startswith("Bonjour")

