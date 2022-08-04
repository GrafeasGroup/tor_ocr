import os

__version__ = "?????"  # replaced by CI pipeline
__BOT_NAMES__ = os.environ.get(
    "BOT_NAMES", "transcribersofreddit,tor_archivist,transcribot,bloosom-app"
).split(",")
