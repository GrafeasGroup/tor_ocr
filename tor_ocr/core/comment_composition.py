import re

# Regex to detect autolinks with a single prefix, e.g. u/username or r/subname
from typing import List

from tor_ocr.core.helpers import _

AUTOLINK_REGEX_SINGLE_PREFIX = re.compile(r"(?P<type>[ur])/(?P<name>\S+)")
# Regex to detect autolinks with a double prefix, e.g. /u/username or /r/subname
AUTOLINK_REGEX_DOUBLE_PREFIX = re.compile(r"/(?P<type>[ur])/(?P<name>\S+)")

# The actual character limit is 10000, but we want to leave some buffer
COMMENT_CHARACTER_LIMIT = 9000


def escape_formatting(text: str) -> str:
    """Escape the Reddit formatting in the given text."""
    # Formatting characters
    text = (
        text.replace("\\", "\\\\")
        .replace("*", r"\*")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )

    # Sub- and usernames
    text = re.sub(AUTOLINK_REGEX_SINGLE_PREFIX, r"\g<type>\/\g<name>", text)
    text = re.sub(AUTOLINK_REGEX_DOUBLE_PREFIX, r"\/\g<type>/\g<name>", text)

    return text


def code_block(text: str) -> str:
    """Put the given text in a markdown code block.

    This prepends four spaces to every line.
    We do not use fenced codeblocks, as they are not supported
    on all devices.
    """
    lines = "\n".split(text)
    code_lines = [f"    {line}" for line in lines]
    return "\n".join(code_lines)


def compose_comments(text: str) -> List[str]:
    """Compose the OCR transcription into Reddit comments.

    This will escape the formatting, put it in a code block,
    add the bot footer and make sure that each comment doesn't
    exceed the character limit.
    """
    escaped_text = code_block(escape_formatting(text))

    def compose_comment(comment_lines: List[str]) -> str:
        """Compose a comment from the given lines.

        This also adds the bot footer.
        """
        return _("\n".join(comment_lines))

    def can_fit_in_comment(comment_lines: List[str], ln: str) -> bool:
        """Determine if the given line can still fit in the comment."""
        comment = compose_comment(comment_lines + [ln])
        return len(comment) < COMMENT_CHARACTER_LIMIT

    comments = []
    cur_comment_lines = []

    for line in "\n".split(escaped_text):
        if not can_fit_in_comment(cur_comment_lines, line):
            # Create a new comment
            comments.append(compose_comment(cur_comment_lines))
            cur_comment_lines = []

        cur_comment_lines.append(line)

    return comments
