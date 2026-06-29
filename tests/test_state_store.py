from state_store import ProcessedState
from token_store import TokenStore


def test_processed_state_is_encrypted_and_reloads(tmp_path):
    key = TokenStore.generate_key()
    store = TokenStore(key)
    path = tmp_path / "processed.enc"
    state = ProcessedState(str(path), store)
    state.complete(client_id="exuvie", connector="gmail", account="main", message_id="m1", thread_id="t1", label="Client", action="draft", draft_created=True)
    assert state.is_processed("exuvie", "gmail", "main", "m1")
    assert b"message_id" not in path.read_bytes()
    reloaded = ProcessedState(str(path), TokenStore(key))
    assert reloaded.get("exuvie", "gmail", "main", "m1")["draft_created"] is True
