import logging
import os
import time

import requests
from tor_core.config import config
# noinspection PyProtectedMember
from tor_core.helpers import _
from tor_core.helpers import clean_id
from tor_core.helpers import run_until_dead
from tor_core.initialize import build_bot

from tor_ocr import __version__
from tor_ocr.errors import OCRError
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

    get link from thingy
    ...OCR magic on link with API...
    save magic

    u_tor_post_id.reply(ocr_magic)
"""

# "helloworld" is a valid API key, however use it sparingly
__OCR_API_KEY__ = os.getenv('OCR_API_KEY', 'helloworld')


def process_image(image_url):
    """
    Processes an image with OCR, using ocr.space
    :param image_url: a string url of what you need OCRed
    :return: A dictionary containing several values, most importantly 'text'
    """
    json_result = decode_image_from_url(image_url)
    try:
        result = {
            'text': json_result.get('ParsedResults')[0]['ParsedText'],
            'exit_code': int(json_result['OCRExitCode']),  # this shouldn't fail
            'error_on_processing': json_result['IsErroredOnProcessing'],
            'error_message': json_result['ErrorMessage'],
            'error_details': json_result['ErrorDetails'],
            # ignores errors per file, we should only get one file ever anyway.
            'process_time_in_ms': int(
                json_result['ProcessingTimeInMilliseconds']
            ),
        }
    except KeyError:
        error_result = {
            'exit_code': json_result['exit_code']
        }
        raise OCRError(error_result)

    # If there's no text, we might get back "", but just in case it's just
    # whitespace, we don't want it.
    if result['text'].strip() == '':
        return None

    if result['exit_code'] != 1 \
            or result['error_on_processing'] \
            or not result['text']:
        raise OCRError(result)

    else:
        return result


def chunks(s, n):
    """
    Produce n-character chunks from s.
    :param s: incoming string.
    :param n: number of characters to cut the chunk at.
    """
    for start in range(0, len(s), n):
        yield s[start:(start + n)]


def decode_image_from_url(url, overlay=False, api_key=__OCR_API_KEY__):
    """
    OCR.space API request with remote file.
    Python3.5 - not tested on 2.7
    This code is stolen from
    https://github.com/Zaargh/ocr.space_code_example/blob/master/ocrspace_example.py
    :param url: Image url.
    :param overlay: Is OCR.space overlay required in your response.
        Defaults to False.
    :param api_key: OCR.space API key.
        Defaults to environment variable "OCR_API_KEY"
        If it doesn't exist, it will use "helloworld"
    :return: Result in JSON format.
    """

    payload = {
        'url': url,
        'isOverlayRequired': overlay,
        'apikey': api_key,
    }

    result = requests.post(
        'https://api.ocr.space/parse/image',
        data=payload,
    )

    # crash and burn if the API is down, or similar :)
    result.raise_for_status()

    return result.json()


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
    url = config.r.submission(id=clean_id(new_post)).url

    try:
        result = process_image(url)
    except OCRError as e:
        logging.warning(
            'There was an OCR Error: ' + str(e)
        )
        return

    logging.debug('result: {}'.format(result))

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

    thing_to_reply_to = tor_post.reply(
        _(base_comment.format(result['process_time_in_ms'] / 1000))
    )

    for chunk in chunks(result['text'], 9000):
        # end goal: if something is over 9000 characters long, we
        # should post a top level comment, then keep replying to
        # the comments we make until we run out of chunks.
        thing_to_reply_to = thing_to_reply_to.reply(
            _(
                chunk.replace(
                    '\r\n', '\n\n'
                ).replace(
                    '/u/', '\\/u/'
                ).replace(
                    '/r/', '\\/r/'
                ).replace(
                    '>>', '\>\>'
                )
            )
        )

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
