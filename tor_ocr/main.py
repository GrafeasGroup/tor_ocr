import argparse
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

import dotenv
import praw
from requests import HTTPError

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

NOOP_MODE = bool(os.getenv('NOOP_MODE', ''))
DEBUG_MODE = bool(os.getenv('DEBUG_MODE', ''))

__VERSION__ = '0.3.0'


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--version', action='version', version=__VERSION__)
    parser.add_argument('--debug', action='store_true', default=DEBUG_MODE, help='Puts bot in dev-mode using non-prod credentials')
    parser.add_argument('--noop', action='store_true', default=NOOP_MODE, help='Just run the daemon, but take no action (helpful for testing infrastructure changes)')

    return parser.parse_args()


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
def run(config: Config) -> None:
    time.sleep(config.ocr_delay)

    new_posts = config.blossom.get_ocr_transcriptions().data
    if len(new_posts) == 0:
        logging.debug("No new posts found; sleeping.")
        return

    logging.info(f"Retrieved {len(new_posts)} unprocessed posts")

    for post in new_posts:
        # There will probably only be one transcription, but if for some reason
        # a volunteer beat us to it, then we'll have to dig ours out of the pile.
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

        # we'll get back a response with a list of one element.
        # noinspection PyUnboundLocalVariable
        data = transcription_obj.data[0]

        tor_post = config.r.submission(url=post["tor_url"])

        try:
            thing_to_reply_to = tor_post.reply(_(base_comment))
        except praw.exceptions.RedditAPIException:
            logging.info("Found post that has aged out; marking as cannot OCR.")
            try:
                config.blossom.patch(
                    f"submission/{get_id_from_url(data['submission'])}", data={"cannot_ocr": True}
                )
            except HTTPError:
                logging.error(f"Updating the Submission {data['submission']} failed.")
            continue
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
        try:
            config.blossom.patch(
                f"transcription/{data['id']}/",
                data={"original_id": comment_id_list[1]},
            )
        except HTTPError:
            logging.error(f"Updating the Transcription {data['id']}"
                          f"'s status in Blossom failed.")


def noop(*args: Any) -> None:
    time.sleep(5)
    logging.info("Loop!")


def main():
    opt = parse_arguments()
    config.ocr_delay = 2
    config.debug_mode = opt.debug
    bot_name = 'debug' if config.debug_mode else os.environ.get('BOT_NAME', 'tor_ocr')

    build_bot(bot_name, __VERSION__)
    if opt.noop:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == "__main__":
    main()
