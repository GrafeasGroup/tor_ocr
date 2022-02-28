import os

__BOT_NAMES__ = os.environ.get(
    "BOT_NAMES", "transcribersofreddit,tor_archivist,transcribot,bloosom-app"
).split(",")
