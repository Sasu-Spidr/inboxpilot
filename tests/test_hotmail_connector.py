from hotmail_connector import HotmailConnector
from token_store import TokenStore

class Resp:
    content=b"x"
    def raise_for_status(self): pass
    def json(self): return {"value":[{"id":"1","subject":"Test","from":{"emailAddress":{"address":"x@y.com"}},"body":{"content":"hello"},"conversationId":"c"}]}
class Session:
    def request(self, *args, **kwargs): return Resp()

def test_reads_unread_email():
    c=HotmailConnector("id","consumers","unused",TokenStore(TokenStore.generate_key()),session=Session()); c.access_token="token"
    assert c.unread_emails(1)[0]["sender"] == "x@y.com"

