import logging
import os
import time
import urllib
from tesserocr import PyTessBaseAPI

import wget
from tor_core.config import config
# noinspection PyProtectedMember
from tor_core.helpers import _
from tor_core.helpers import clean_id
from tor_core.helpers import run_until_dead
from tor_core.initialize import build_bot

from tor_ocr import __version__
from tor_ocr.strings import base_comment

"""
General notes for implementation.

Process:

u/transcribersofreddit identifies an image
  config.redis.rpush('ocr_ids', 'ocr::{}'.format(post.fullname))
  config.redis.set('ocr::{}'.format(post.fullname), result.fullname)

...where result.fullname is the post that u/transcribersofreddit makes about
the image.

Bot:
  every interval (variable):
    thingy = config.redis.lpop('ocr_ids')
    u_tor_post_id = config.redis.get(thingy)

    get image from thingy
    download it
    ...OCR magic on thingy...
    save magic
    delete image

    u_tor_post_id.reply(ocr_magic)
"""


def process_image(local_file):
    with PyTessBaseAPI() as api:
        api.SetImageFile(local_file)
        text = api.GetUTF8Text()

        confidences = api.AllWordConfidences()
        if not confidences or len(confidences) == 0:
            # we have an image, but it *really* couldn't find anything, not
            # even false positives.
            return None

        logging.debug('Average of confidences: {}'.format(
            sum(confidences) / len(confidences))
        )

        # If you feed it a regular image with no text, more often than not
        # you'll get newlines and spaces back. We strip those out to see if
        # we actually got anything of substance.
        if text.strip() != '':
            return text
        else:
            return None


def chunks(s, n):
    """
    Produce n-character chunks from s.
    :param s: incoming string.
    :param n: number of characters to cut the chunk at.
    """
    for start in range(0, len(s), n):
        yield s[start:(start + n)]


def run(config):

    time.sleep(config.ocr_delay)
    new_post = config.redis.lpop('ocr_ids')
    if new_post is None:
        logging.debug('No post found. Sleeping.')
        # nothing new in the queue. Wait and try again.
        # Yes, I know this is outside a loop. It will be run inside a loop
        # by tor_core.
        return

    # We got something!
    new_post = new_post.decode('utf-8')
    logging.info(
        'Found a new post, ID {}'.format(new_post)
    )
    image_post = config.r.submission(id=clean_id(new_post))

    # download image for processing
    # noinspection PyUnresolvedReferences
    try:
        filename = wget.download(image_post.url)
    except urllib.error.HTTPError:
        # what if the post has been deleted? Ignore it and continue.
        return

    try:
        result = process_image(filename)
    except RuntimeError:
        logging.warning(
            'Either we hit an imgur album or no text was returned.'
        )
        os.remove(filename)
        return

    logging.debug('result: {}'.format(result))

    # delete the image; we don't want to clutter up the HDD
    os.remove(filename)

    if not result:
        logging.info('Result was none! Skipping!')
        # we don't want orphan entries
        config.redis.delete(new_post)
        return

    tor_post_id = config.redis.get(new_post).decode('utf-8')

    logging.info(
        'posting transcription attempt for {} on {}'.format(
            new_post, tor_post_id
        )
    )

    tor_post = config.r.submission(id=clean_id(tor_post_id))

    thing_to_reply_to = tor_post.reply(_(base_comment))
    for chunk in chunks(result, 9000):
        # end goal: if something is over 9000 characters long, we
        # should post a top level comment, then keep replying to
        # the comments we make until we run out of chunks.
        thing_to_reply_to = thing_to_reply_to.reply(_(chunk))

    config.redis.delete(new_post)


def main():
    """
        Console scripts entry point for OCR Bot
    """

    build_bot('bot_ocr',
              __version__,
              full_name='u/transcribot',
              log_name='ocr.log')
    config.ocr_delay = 10
    run_until_dead(run)


if __name__ == '__main__':
    main()
