# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## [UNRELEASED]

- "Source" link in the bot footer now redirects to this repo instead of the u/tor one
- Added processing for inbox, respond to a user replying to bot's comment (credit: @crhopkins)

## [0.2.3] -- 2021-04-05

- Odd error with PRAW in https://github.com/GrafeasGroup/tor necessitates a core library upgrade

## [0.2.2] -- 2021-01-26

- Converts `setup.py` to Poetry tooling for easier development and package management
- Makes cleaning the Reddit ID more resilient (passing an already-clean id through without issue)
- CLI args for better testing

## [0.2.1] -- 2019-06-16

- FIX: Timeout in talking with <https://OCR.space/> when only waiting 2 seconds

## [0.2.0] -- 2019-06-16

- Pulls in `tor_core` as `tor_ocr.core`
- Adds `tox` as a way of invoking tests in lieu of `python setup.py test`
- Introduces No Operation (NOOP) mode for basic smoke-testing of code without affecting external services

## [0.1.0]

- Initial split from `tor` into one package per bot
