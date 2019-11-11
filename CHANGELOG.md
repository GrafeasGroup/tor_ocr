# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## [UNRELEASED]

- Converts `setup.py` to Poetry tooling for easier development and package management

## [0.2.1] -- 2019-06-16

- FIX: Timeout in talking with <https://OCR.space/> when only waiting 2 seconds

## [0.2.0] -- 2019-06-16

- Pulls in `tor_core` as `tor_ocr.core`
- Adds `tox` as a way of invoking tests in lieu of `python setup.py test`
- Introduces No Operation (NOOP) mode for basic smoke-testing of code without affecting external services

## [0.1.0]

- Initial split from `tor` into one package per bot
