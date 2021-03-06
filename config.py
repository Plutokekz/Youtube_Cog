import configparser
import os

config = configparser.ConfigParser()
path = os.path.join(f"{os.sep}".join(os.path.abspath(__file__).split(os.sep)[:-1]), "config.ini")
config.read(path)

YTDL_OPTIONS = dict(config.items("ytdl"))
for key, value in YTDL_OPTIONS.items():
    if value == "True":
        YTDL_OPTIONS[key] = True
    elif value == "False":
        YTDL_OPTIONS[key] = False

FFMPEG_OPTIONS = dict(config.items("ffmpeg"))

DISCORD = dict(config.items("discord"))
DISCORD['volume'] = float(DISCORD["volume"])
DISCORD["roles"] = DISCORD["roles"].split(",")

