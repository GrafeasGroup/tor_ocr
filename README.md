[![Stories in Ready](https://badge.waffle.io/TranscribersOfReddit/ToR_OCR.png?label=ready&title=Ready)](http://waffle.io/TranscribersOfReddit/ToR_OCR)

[![BugSnag](https://img.shields.io/badge/errors--hosted--by-BugSnag-blue.svg)](https://www.bugsnag.com/open-source/)

# Apprentice Bot - Transcribers Of Reddit

This is the source code for Apprentice Bot (`/u/transcribot`). It forms one part
of the team that assists in the running or /r/TranscribersOfReddit (ToR), which
is privileged to have the incredibly important job of organizing crowd-sourced
transcriptions of images, video, and audio.

As a whole, the ToR bots are designed to be as light on local resources as they
can be, though there are some external requirements.

- Redis (tracking completed posts and queue system)
- Tesseract (OCR solution)

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains information such as the useragents and certain secrets. It is built
> for Python 3.6.

## Installation

```
$ git clone https://github.com/TranscribersOfReddit/ToR_OCR.git tor-ocr
$ pip install --process-dependency-links tor-ocr/
```

OR

```
$ pip install --process-dependency-links 'git+https://github.com/TranscribersOfReddit/ToR_OCR.git@master#egg=tor_ocr'
```

## High-level functionality

Monitoring daemon (via Redis queue):

- Pull job (by post id) off of queue:
  - Download image
  - OCR the image
  - If OCR successful:
    - Post OCR-ed content to post on /r/TranscribersOfReddit in 9000 character chunks
  - Delete local copy of image

### Running Apprentice Bot

```
$ tor-apprentice
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
