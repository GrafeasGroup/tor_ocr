[![BugSnag](https://img.shields.io/badge/errors--hosted--by-Bugsnag-blue.svg)](https://www.bugsnag.com/open-source/)

# Apprentice Bot - Transcribers Of Reddit

This is the source code for a helper bot, making attempts at transcribing content as
it is posted to the subreddit /r/TranscribersOfReddit, a community dedicated to
transcribing images, audio, and video. It acts under the username "/u/transcribot".

This bot is still in training and might not be able to recognize everything it
attempts. Some transcriptions might be complete trash, but the hope is that it will
be a start to a more legitimate, volunteer-written transcription.

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains information such as the useragents and certain secrets. It is built
> for Python 3.8.

If wanting to install from source, clone the repo, install [poetry](https://poetry.eustace.io), and run `poetry install`:

```
$ git clone git@github.com:GrafeasGroup/tor_ocr.git ./tor_ocr
$ cd ./tor_ocr
$ pip install poetry
$ poetry install
```

## High-level functionality

- Ask [Blossom](https://github.com/grafeasgroup/blossom) for posts that have an OCR transcription that hasn't been posted yet
  - Post OCR-ed content to post on /r/TranscribersOfReddit in 9000 character chunks, replying to previous comment when [over 9000][over-9000] characters

[over-9000]: https://tenor.com/view/dragonball-z-super-saiyan-charging-yelling-gif-4987448

### Running the Bot

```bash
$ ./tor_ocr.pyz
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
