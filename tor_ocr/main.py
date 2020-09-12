import logging
import os
import time
from urllib.parse import urlparse

import pkg_resources

from tor_ocr.core.config import config
from tor_ocr.core.helpers import _, run_until_dead
from tor_ocr.core.initialize import build_bot
from tor_ocr.strings import base_comment

"""
General notes for implementation.

Process:

Reach out to Blossom for post objects
- for each submission, get the auto-generated OCR text from Blossom
- post the auto-generated OCR text on each submission
- patch back the reddit ID of the primary comment back to Blossom
"""

NOOP_MODE = bool(os.getenv("NOOP_MODE", ""))
DEBUG_MODE = bool(os.getenv("DEBUG_MODE", ""))


def chunks(s: str, n: int) -> str:
    """
    Produce n-character chunks from s.

    :param s: incoming string.
    :param n: number of characters to cut the chunk at.
    """
    for start in range(0, len(s), n):
        yield s[start: (start + n)]


def get_id_from_url(url: str) -> int:
    """Extract and return the ID from the end of a Blossom URL."""
    return int(list(filter(None, urlparse(url).path.split("/")))[-1])


# noinspection PyShadowingNames
def run(config):
    time.sleep(config.ocr_delay)

    new_posts = config.blossom.get_ocr_transcriptions().data
    if len(new_posts) == 0:
        logging.debug("No new posts found; sleeping.")
        return

    logging.info(f"Retrieved {len(new_posts)} unprocessed posts")

    for post in new_posts:
        # there should be two transcriptions: one from the volunteer
        # and one from us. Need to find ours.
        found_our_own_transcription = False
        for transcription_url in post["transcription_set"]:
            transcription_obj = config.blossom.get_transcription(
                id=get_id_from_url(transcription_url)
            )
            if get_id_from_url(transcription_obj.data[0]["author"]) != config.me["id"]:
                continue
            found_our_own_transcription = True
            logging.debug("Found our transcription!")
            break

        if not found_our_own_transcription:
            # how did we get here? We must not have found our own work from the API...
            # that would be a Blossom error. Skip this post.
            logging.error(
                f"It looks like we got a post without a transcription..."
                f" check submission {post['id']}"
            )
            continue

        # noinspection PyUnboundLocalVariable
        data = transcription_obj.data[0]

        tor_post = config.r.submission(url=post["tor_url"])

        thing_to_reply_to = tor_post.reply(_(base_comment))

        # we need to keep track of each of the comments we create in case this
        # is a really long transcription. We want to send blossom the ID of the
        # comment that actually starts the transcription, which should always
        # be object 1 in the list (object 0 is the "hi I'm a bot" message).
        comment_id_list = [thing_to_reply_to.fullname]

        for chunk in chunks(data["text"], 9000):
            # end goal: if something is over 9000 characters long, we
            # should post a top level comment, then keep replying to
            # the comments we make until we run out of chunks.
            thing_to_reply_to = thing_to_reply_to.reply(_(chunk))
            comment_id_list += [thing_to_reply_to.fullname]

        logging.info(f"Patching {data['id']}...")
        config.blossom.patch(
            f"transcription/{data['id']}/",
            data={"original_id": comment_id_list[1]},
        )


def noop(cfg):
    time.sleep(5)
    logging.info("Loop!")


def main():
    config.ocr_delay = 20
    config.debug_mode = DEBUG_MODE
    bot_name = "debug" if config.debug_mode else os.environ.get("BOT_NAME", "bot_ocr")

    build_bot(bot_name, pkg_resources.get_distribution("tor_ocr").version)

    if NOOP_MODE:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == "__main__":
    main()
