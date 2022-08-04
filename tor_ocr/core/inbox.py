import logging
import praw

from tor_ocr.core.config import Config
from tor_ocr.core.helpers import _
from tor_ocr.strings import reply_response
from tor_ocr import __BOT_NAMES__

log = logging.getLogger(__name__)


def is_comment_reply(message: praw.models.Message) -> bool:
    """
    Determines if a message from the inbox is from a reply to one of the bot's comments
    This is determined by checking the message's subject is 'post reply'

    :return: Boolean for if the message is from a comment reply
    """
    return message.subject == "post reply"


def process_message(message: praw.models.Message) -> None:
    """
    This function will handle each message coming from the inbox.
    Currently, it only responds to comments
    """
    if is_comment_reply(message):
        message.reply(_(reply_response))


def check_inbox(config: Config) -> None:
    """
    Goes through all the unread messages in the inbox.
    Messages are first checked that they have an author and are not
    one of the TOR bots.
    Each message is then sent to process_message() for furhter handling
    Each message is also marked as read, leaving the inbox clear with
    each call of this method.

    :return: None.
    """
    # Sort inbox, then act on it
    # Invert the inbox so we're processing oldest first!
    for item in reversed(list(config.r.inbox.unread(limit=None))):
        # Since we grabbed the inbox.unread, all should be unread,
        # but lets do a quick check first to be sure
        if item.new:
            # Very rarely we may actually get a message from Reddit itself.
            # In this case, there will be no author attribute.
            author_name = item.author.name if item.author else None
            if author_name is None:
                # This is likely a message from reddit, and doesn't need a
                # response. So just log it, and move on
                log.info("Received a message without an author.")
                log.info(f"Subject: '{item.subject}' Body: '{item.body}'")
            elif author_name in __BOT_NAMES__:
                # ignore anything from one of our other bots
                log.info(f"Ignoring a message from one of our bots (${item.author.name})")
            else:
                process_message(item)

        # Mark as read so we don't process it again
        item.mark_read()

    log.info("processed inbox")
