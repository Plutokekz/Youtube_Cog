import asyncio
import functools

import discord
import youtube_dl
from discord.ext import commands

from . import YTDL_OPTIONS, FFMPEG_OPTIONS, DISCORD

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict,
                 volume: float = DISCORD['volume']):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        # date = data.get('upload_date')
        self.upload_date = "22.02.2022"  # date[6:8] + '.' + date[4:6] + '.' + date[0:4] if data else None
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return f'**{self.title}** by **{self.uploader}**'

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(f'Couldn\'t find anything that matches `{search}`')

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(f'Couldn\'t find anything that matches `{search}`')

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError(f'Couldn\'t fetch `{webpage_url}`')

        info = {
            "uploader": "Unknown",
            "uploader_url": "-",
            "upload_date": "22.02.2022",
            "title": "-",
            "thumbnail": "https://www.silvaporto.com.br/wp-content/uploads/2017/08/default_thumbnail-768x576.jpg",
            "description": "-",
            "duration": 100,
            "tags": "-",
            "webpage_url": "https://dasendedesinternet.de/",
            "view_count": "0",
            "like_count": "0",
            "dislike_count": "0",
            "url": "https://dasendedesinternet.de/"
        }

        if 'entries' not in processed_info:
            info.update(processed_info)
        else:
            info = None
            while info is None:
                try:
                    info = {
                        "uploader": "Unknown",
                        "uploader_url": "-",
                        "upload_date": "22.02.2022",
                        "title": "-",
                        "thumbnail": "https://www.silvaporto.com.br/wp-content/uploads/2017/08/default_thumbnail-768x576.jpg",
                        "description": "-",
                        "duration": 100,
                        "tags": "-",
                        "webpage_url": "https://dasendedesinternet.de/",
                        "view_count": "0",
                        "like_count": "0",
                        "dislike_count": "0",
                        "url": "https://dasendedesinternet.de/"
                    }
                    info.update(processed_info['entries'].pop(0))
                except IndexError:
                    raise YTDLError(f'Couldn\'t retrieve any matches for `{webpage_url}`')
        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def to_audio_source(self):
        return self.source

    def to_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed
