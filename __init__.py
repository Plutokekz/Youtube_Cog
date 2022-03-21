"""
Youtube-dl Discord Cog

:copyright: (c) 2022 Plutokekz

"""

__title__ = 'youtube_cog'
__author__ = 'Plutokekz'
__copyright__ = 'Copyright 2022 Plutokekz'
__version__ = '0.1'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

from .config import DISCORD, YTDL_OPTIONS, FFMPEG_OPTIONS
from .MusicPlayer import MusicPlayer
