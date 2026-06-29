from gmail_connector import GmailConnector
from token_store import TokenStore

class Execute:
    def __init__(self, result): self.result=result
    def execute(self): return self.result
class Messages:
    def list(self, **kwargs): return Execute({"messages":[{"id":"m1"}]})
    def get(self, **kwargs): return Execute({"threadId":"t1","payload":{"headers":[{"name":"Subject","value":"Hello"},{"name":"From","value":"x@y.com"}],"body":{"data":"SGk="}}})
class Users:
    def messages(self): return Messages()
class Service:
    def users(self): return Users()

def test_reads_unread_email():
    c=GmailConnector("unused","unused",TokenStore(TokenStore.generate_key()),service=Service())
    assert c.unread_emails(1) == [{"id":"m1","subject":"Hello","sender":"x@y.com","body":"Hi","thread_id":"t1"}]

