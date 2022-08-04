import pytest

from tor_ocr.main import get_id_from_url


@pytest.mark.parametrize(
    "url,value", [
        ("https://a.z/abc/123", 123),
        ("https://a.z/abc/1", 1)
    ]
)
def test_get_id_from_url(url: str, value: int) -> None:
    assert get_id_from_url(url) == value
