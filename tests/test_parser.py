import json

from xueqiu_collector.errors import ResponseKind, classify_response
from xueqiu_collector.parser import parse_timeline_payload
from xueqiu_collector.text import normalize_html_text


def test_normalize_html_text_strips_tags_and_entities():
    html = "<p>hello&nbsp;<a href='/S/SH000001'>$SH000001</a>&amp; more</p>"

    assert normalize_html_text(html) == "hello $SH000001 & more"


def test_parse_timeline_payload_accepts_home_timeline_items():
    payload = {
        "home_timeline": [
            {
                "id": 123,
                "created_at": 1710000000000,
                "text": "<p>first&nbsp;post</p>",
                "user": {"id": 456, "screen_name": "alice"},
                "reply_count": 2,
                "retweet_count": 3,
                "fav_count": 4,
            }
        ]
    }

    posts = parse_timeline_payload(payload)

    assert len(posts) == 1
    assert posts[0].id == "123"
    assert posts[0].author_id == "456"
    assert posts[0].author_name == "alice"
    assert posts[0].created_at == "2024-03-09T16:00:00+00:00"
    assert posts[0].text == "first post"
    assert posts[0].url == "https://xueqiu.com/456/123"
    assert posts[0].reply_count == 2
    assert json.loads(posts[0].raw_json)["id"] == 123


def test_classify_response_detects_login_error_from_status():
    result = classify_response(401, "{\"error_description\":\"not logged in\"}")

    assert result.kind == ResponseKind.UNAUTHORIZED
    assert "run xueqiu-collector auth" in result.message


def test_classify_response_detects_malformed_json():
    result = classify_response(200, "{broken")

    assert result.kind == ResponseKind.MALFORMED_JSON
    assert "malformed JSON" in result.message
