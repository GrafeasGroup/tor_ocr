import logging
import os

from blossom_wrapper import BlossomAPI
from bugsnag.handlers import BugsnagHandler
from praw import Reddit

from tor_ocr.core.config import config
from tor_ocr.core.helpers import log_header


def configure_logging(config):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # will intercept anything error level or above
    if config.bugsnag_api_key:
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger("").addHandler(bs_handler)
        logging.info("Bugsnag enabled!")
    else:
        logging.info("Not running with Bugsnag!")

    log_header("Starting!")


def get_blossom_connection():
    return BlossomAPI(
        email=os.getenv("BLOSSOM_EMAIL"),
        password=os.getenv("BLOSSOM_PASSWORD"),
        api_key=os.getenv("BLOSSOM_API_KEY"),
    )


def get_me_info(config):
    return config.blossom.get(
        "volunteer/", params={"username": "transcribot"}
    ).json()["results"][0]


def build_bot(name, version):
    """
    Shortcut for setting up a bot instance. Runs all configuration and returns
    a valid config object.

    :param name: string; The name of the bot to be started; this name must
        match the settings in praw.ini
    :param version: string; the version number for the current bot being run
    :param full_name: string; the descriptive name of the current bot being
        run
    :return: None
    """

    config.r = Reddit(name)
    config.bot_version = version
    configure_logging(config)
    config.blossom = get_blossom_connection()
    config.me = get_me_info(config)

    logging.info("Bot built and initialized!")
