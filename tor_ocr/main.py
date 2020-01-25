import logging
import os
import re
import time

import requests
from requests.exceptions import ConnectTimeout, RequestException
from tor_ocr.core.blossom import BlossomAPI

from tor_ocr import __version__
from tor_ocr.core.config import config
from tor_ocr.core.helpers import _, clean_id, run_until_dead
from tor_ocr.core.initialize import build_bot
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
# __OCR_API_URLS__ = ['https://api.ocr.space/parse/image']  # free API url
__OCR_API_URLS__ = [
    'https://apipro1.ocr.space/parse/image',  # USA
    'https://apipro2.ocr.space/parse/image',  # Europe
    'https://apipro3.ocr.space/parse/image'  # Asia
]

NOOP_MODE = bool(os.getenv('NOOP_MODE', ''))
DEBUG_MODE = bool(os.getenv('DEBUG_MODE', ''))


def process_image(image_url):
    """
    Processes an image with OCR, using ocr.space
    :param image_url: a string url of what you need OCRed
    :return: A dictionary containing several values, most importantly 'text'
    """

    def _set_error_state(response):
        # In the event of an error, build a "lite" version of the response dict
        # and use that to present an error message.
        error = {
            'exit_code': response['OCRExitCode'],
            'error_message': json_result.get('ErrorMessage'),
            'error_details': json_result.get('ErrorDetails')
        }
        return error

    json_result = decode_image_from_url(image_url)

    if json_result.get('ParsedResults') is None:
        raise OCRError(_set_error_state(json_result))

    try:
        result = {
            'text': json_result['ParsedResults'][0]['ParsedText'],
            'exit_code': int(json_result['OCRExitCode']),
            # this will change depending on how many pages we send it
            'page_exit_code': int(
                json_result['ParsedResults'][0]['FileParseExitCode']
            ),
            'error_on_processing': json_result['IsErroredOnProcessing'],
            # the API has stopped returning these two fields. The documentation
            # says that it should still be there, but they're only there on
            # an actual error now. We'll still keep looking for the fields, but
            # we won't make them required. First seen on 8/13/18
            'error_message': json_result.get('ErrorMessage', ''),
            'error_details': json_result.get('ErrorDetails', ''),
            # ignores errors per file, we should only get one file ever anyway.
            'process_time_in_ms': int(
                json_result['ProcessingTimeInMilliseconds']
            ),
        }
    except (KeyError, IndexError):
        raise OCRError(_set_error_state(json_result))

    # If there's no text, we might get back "", but just in case it's just
    # whitespace, we don't want it.
    if result['text'].strip() == '':
        return None

    if result['exit_code'] != 1 \
            or result['error_on_processing'] \
            or not result['text']:
        raise OCRError(_set_error_state(json_result))

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
    This code was originally borrowed from
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

    result = None

    for API in __OCR_API_URLS__:
        try:
            # The timeout for this request goes until the first bit response,
            # not for the entire request process. If we don't hear anything
            # from the remote server for 2 seconds, throw a ConnectTimeout
            # and move on to the next one.
            result = requests.post(API, data=payload, timeout=10)
            # crash and burn if the API is down, or similar
            result.raise_for_status()

            if result.json()['OCRExitCode'] == 6:
                # process timed out waiting for response
                raise ConnectionError

            # if the request succeeds, we'll have a result. Therefore, just
            # break the loop here.
            break
        except ConnectTimeout:
            # Sometimes the ocr.space API will just... not respond. Move on.
            continue
        except ConnectionError:
            # try the next API in the list, then release from the loop if we
            # exhaust our options.
            continue
        except RequestException as e:
            # we have a result object here but it's not right.
            if result is None:
                logging.warning(
                    f'Received null object because of a request exception. '
                    f'Attempted API: {API} | Error: {e}'
                )
            else:
                logging.error(
                    f'ERROR {result.status_code} with OCR:\n\nHEADERS:\n '
                    f'{repr(result.headers)}\n\nBODY:\n{repr(result.text)} '
                )

    if result is None or not result.ok:
        raise ConnectionError(
            'Attempted all three OCR.space APIs -- cannot connect!'
        )

    return result.json()


def escape_reddit_links(body):
    r"""
    Escape u/ and r/ links in a message so we don't get confused redditors
    commenting on transcribot.
    There is no (known) way to escape u/ or r/ (without a preceding slash),
    so those will also be changed to \/u/ and \/r/.
    :param body: the text to escape
    :return: the escaped text
    """
    magic = re.compile('(?<![a-zA-Z0-9])([ur])/|/([ur])/')
    return magic.sub(r'\/\1\2/', body)


# noinspection PyShadowingNames
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
        f'Found a new post, ID {new_post}'
    )

    b = BlossomAPI(email='joe@grafeas.org', password='asdf', api_key="el9qKhdv.kTokbAbt1kyfhCQattZyxXLneKoEBHGZ")
    blossom_submission = b.get("/submission/2/").json()
    logging.info(blossom_submission)

    url = config.r.submission(id=clean_id(new_post)).url
    try:
        result = process_image(url)
    except OCRError as e:
        logging.warning(
            'There was an OCR Error: ' + str(e)
        )
        return

    logging.debug(f'result: {result}')

    if not result:
        logging.info('Result was none! Skipping!')
        # we don't want orphan entries
        config.redis.delete(new_post)
        return

    tor_post_id = config.redis.get(new_post).decode('utf-8')

    logging.info(
        f'posting transcription attempt for {new_post} on {tor_post_id}'
    )

    tor_post = config.r.submission(id=clean_id(tor_post_id))

    thing_to_reply_to = tor_post.reply(
        _(base_comment.format(result['process_time_in_ms'] / 1000))
    )

    for chunk in chunks(result['text'], 9000):
        # end goal: if something is over 9000 characters long, we
        # should post a top level comment, then keep replying to
        # the comments we make until we run out of chunks.

        chunk = escape_reddit_links(
            chunk.replace(
                '\r\n', '\n\n'
            ).replace(
                '>>', r'\>\>'
            )
        )

        thing_to_reply_to = thing_to_reply_to.reply(_(chunk))

    config.redis.delete(new_post)


def noop(cfg):
    time.sleep(5)
    logging.info('Loop!')


def main():
    config.ocr_delay = 2
    config.debug_mode = DEBUG_MODE
    bot_name = 'debug' if config.debug_mode else os.environ.get('BOT_NAME', 'bot_ocr')

    build_bot(bot_name, __version__, full_name='u/transcribot')
    if NOOP_MODE:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == '__main__':
    main()
