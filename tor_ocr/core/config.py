import datetime
import os

# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag
except ImportError:
    # If loading from setup.py or bugsnag isn't installed, we
    # don't want to bomb out completely
    bugsnag = None

import pkg_resources

_missing = object()


# @see https://stackoverflow.com/a/17487613/1236035
class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is no
    # entry with the same name in the instance's __dict__. this allows
    # us to completely get rid of the access function call overhead. If
    # one choses to invoke __get__ by hand the property will still work
    # as expected because the lookup logic is replicated in __get__ for
    # manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, _type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


class Config(object):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    # API key for later overwriting based on contents of filesystem
    bugsnag_api_key = None

    debug_mode = False

    # Global flag to enable/disable placing the triggers
    # for the OCR bot
    OCR = True

    # Name of the bot
    name = None
    bot_version = '0.0.0'  # this should get overwritten by the bot process

    last_post_scan_time = datetime.datetime(1970, 1, 1, 1, 1, 1)

    @cached_property
    def tor(self):
        if self.debug_mode:
            return self.r.subreddit('ModsOfTor')
        else:
            return self.r.subreddit('transcribersofreddit')


try:
    Config.bugsnag_api_key = open('bugsnag.key').readline().strip()
except OSError:
    Config.bugsnag_api_key = os.environ.get('BUGSNAG_API_KEY', None)

if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(
        api_key=Config.bugsnag_api_key,
        app_version=pkg_resources.get_distribution('tor_ocr').version
    )

# ----- Compatibility -----
config = Config()
