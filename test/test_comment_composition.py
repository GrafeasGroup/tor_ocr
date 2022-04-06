import pytest

from tor_ocr.core.comment_composition import (
    escape_formatting,
    code_block,
    compose_comments,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Asd normal text bla bla, this is nice.",
            "Asd normal text bla bla, this is nice.",
        ),
        (
            "Text with **bold** and **more bold**.",
            r"Text with \*\*bold\*\* and \*\*more bold\*\*.",
        ),
        (
            "> Quoting things",
            r"\> Quoting things",
        ),
        (
            "Text with *italics* and *more italics*.",
            r"Text with \*italics\* and \*more italics\*.",
        ),
        (
            "Text with _italics_ and _more italics_.",
            r"Text with \_italics\_ and \_more italics\_.",
        ),
        (
            "#hashtag",
            r"\#hashtag",
        ),
        (
            "A u/username and other /u/_user123_.",
            r"A u\/username and other \/u/\_user123\_.",
        ),
        (
            "A r/subname and other /r/_sub123_.",
            r"A r\/subname and other \/r/\_sub123\_.",
        ),
    ],
)
def test_escape_formatting(text: str, expected: str) -> None:
    """Test that Reddit formatting is escaped correctly."""
    actual = escape_formatting(text)
    assert actual == expected


def test_code_block() -> None:
    """Test that code blocks are created correctly."""
    text = "abc\nde\nfghi"
    expected = "    abc\n    de\n    fghi"
    actual = code_block(text)

    assert actual == expected


def test_compose_comments_single() -> None:
    """Test that the text is included in the comment."""
    text = "This is a nice test text."
    actual = compose_comments(text)

    assert len(actual) == 1
    assert text in actual[0]


def test_compose_comments_multiple() -> None:
    """Test that the text is split if necessary"""
    line = "This is a nice test text."
    lines = []
    for i in range(5000):
        lines.append(line)

    text = "\n".join(lines)
    actual = compose_comments(text)

    assert len(actual) > 1
