from internal_ai_api.request_ids import request_id


def test_request_id_rejects_path_and_log_injection():
    assert request_id("client_123") == "client_123"
    generated = request_id("../outside\nforged")
    assert generated.startswith("req_")
    assert "/" not in generated

