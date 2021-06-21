import argparse
import logging
import os
import time
from typing import Any, List
from typing import Dict, Optional
from urllib.parse import urlparse

import dotenv
import praw

from tor_ocr.core.config import config, Config
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
dotenv.load_dotenv()

NOOP_MODE = bool(os.getenv("NOOP_MODE", ""))
DEBUG_MODE = bool(os.getenv("DEBUG_MODE", ""))

__VERSION__ = "0.3.0"


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--version", action="version", version=__VERSION__)
    parser.add_argument(
        "--debug",
        action="store_true",
        default=DEBUG_MODE,
        help="Puts bot in dev-mode using non-prod credentials",
    )
    parser.add_argument(
        "--noop",
        action="store_true",
        default=NOOP_MODE,
        help="Just run the daemon, but take no action (helpful for testing infrastructure changes)",
    )

    return parser.parse_args()


def chunks(s: str, n: int) -> str:
    """
    Produce n-character chunks from s.

    :param s: incoming string.
    :param n: number of characters to cut the chunk at.
    """
    for start in range(0, len(s), n):
        yield s[start : (start + n)]


def get_id_from_url(url: str) -> int:
    """Extract and return the ID from the end of a Blossom URL."""
    return int(list(filter(None, urlparse(url).path.split("/")))[-1])


# noinspection PyShadowingNames
def run(config: Config) -> None:
    time.sleep(config.ocr_delay)

    new_posts: Optional[
        List[Dict[str, Any]]
    ] = config.blossom.get_ocr_transcriptions().data
    if len(new_posts) == 0:
        logging.debug("No new posts found; sleeping.")
        return

    logging.info(f"Retrieved {len(new_posts)} unprocessed posts")

    for ocr_obj in new_posts:
        # Each ocr_obj looks like this:
        # {
        #   'id': 1,  # blossom submission ID
        #   'tor_url': None,  # the url to the ToR post
        #   'transcription__id': 1,  # blossom ID of the transcription
        #   'transcription__text': 'aaaa...'  # what it says
        # }

        tor_post = config.r.submission(url=ocr_obj["tor_url"])

        try:
            thing_to_reply_to = tor_post.reply(_(base_comment))
        except praw.exceptions.RedditAPIException:
            logging.info("Found post that has aged out; marking as cannot OCR.")
            config.blossom.patch(
                f"submission/{ocr_obj['id']}", data={"cannot_ocr": True}
            )
            continue
        # we need to keep track of each of the comments we create in case this
        # is a really long transcription. We want to send blossom the ID of the
        # comment that actually starts the transcription, which should always
        # be object 1 in the list (object 0 is the "hi I'm a bot" message).
        comment_id_list = [thing_to_reply_to.fullname]

        for chunk in chunks(ocr_obj["text"], 9000):
            # end goal: if something is over 9000 characters long, we
            # should post a top level comment, then keep replying to
            # the comments we make until we run out of chunks.
            thing_to_reply_to = thing_to_reply_to.reply(_(chunk))
            comment_id_list += [thing_to_reply_to.fullname]

        logging.info(f"Patching {ocr_obj['transcription__id']}...")
        config.blossom.patch(
            f"transcription/{ocr_obj['transcription__id']}/",
            data={"original_id": comment_id_list[1]},
        )


def noop(*args: Any) -> None:
    time.sleep(5)
    logging.info("Loop!")


def main():
    opt = parse_arguments()
    config.ocr_delay = 2
    config.debug_mode = opt.debug
    bot_name = "debug" if config.debug_mode else os.environ.get("BOT_NAME", "tor_ocr")

    build_bot(bot_name, __VERSION__)
    if opt.noop:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == "__main__":
    main()
