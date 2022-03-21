import asyncio
import logging
import sys
import traceback

import discord
from discord.ext import commands
from discord.utils import get

from MusicPlayer import MusicPlayer
from Youtube import YTDLSource, YTDLError, Song
from config import DISCORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


def check_role(roles: [str] = DISCORD["roles"]):
    """
    Decorator to check if the author from the message as a role from the roles list
    :param roles: a list of role names
    :return: commands.check()
    """
    def predicate(ctx):
        print([x.name for x in ctx.message.author.roles])
        for role in roles:
            if role in [x.name for x in ctx.message.author.roles]:
                return True
        return False

    return commands.check(predicate)


class PlaySounds(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.players = {}
        self.messages = []
        self.vc = None

    @commands.command(name='play')
    @check_role()
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        channel = ctx.voice_client
        self.messages.append(ctx.message)
        if not channel:
            await ctx.invoke(self._connect)
        player = self.get_player(ctx)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=ctx.bot.loop)
            except YTDLError as e:
                logger.warning(f"An error occurred while processing this request: {str(e)}, with request {search}")
                await ctx.send(f'Kann ich oder darf ich nicht ab spielen {search}')
            else:
                song = Song(source)
                logger.info(f"queuing {song.source.title}")
                await player.queue.put(song)
        await ctx.message.delete(delay=10)

    @commands.command(name='disconnect')
    @check_role()
    async def _disconnect(self, context):
        """Disconnects the Bot from the current voice channel."""
        self.messages.append(context.message)
        vc = context.voice_client
        if vc:
            await vc.disconnect()
        await context.message.delete(delay=10)

    @staticmethod
    async def _send_error_msg(context, e):
        await context.message.channel.send(f'Error: {str(e)}', delete_after=5)

    @commands.command(name='connect', aliases=['join'])
    @check_role()
    async def _connect(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect the Bot to the voice channel of the author."""
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                await self._send_error_msg(ctx,
                                           f'{ctx.message.author.name}, Sie befinden sich nicht ein einem Sprach Kanal')
                logger.warning(f"{ctx.message.author.name} is currently not in a voice channel")
        vc = ctx.voice_client  # await channel.connect()
        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                await self._send_error_msg(ctx, f'Get Nicht: <{channel}> Zeit aus.')
                logger.warning(f"Error timeout for: {channel}")
        else:
            try:

                await channel.connect()

            except asyncio.TimeoutError:
                await self._send_error_msg(ctx, f'Get Nicht: <{channel}> Zeit aus.')
                logger.warning(f"Error timeout for: {channel}")

        await ctx.send(f'Sie sind verbunden mit: **{channel}**', delete_after=10)
        logger.info(f"Bot connect with: {channel}")
        await ctx.message.delete(delay=10)

    @commands.command(name='pause')
    @check_role()
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""
        vc = ctx.voice_client
        if vc.is_playing:
            vc.pause()
            emoji = get(self.client.emojis, name='DarksideDeutscheBahn')
            await ctx.message.add_reaction(emoji)
            logger.info(f"pausing")
        await ctx.message.delete(delay=10)

    @commands.command(name='resume')
    @check_role()
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""
        vc = ctx.voice_client
        if vc.is_paused():
            vc.resume()
            emoji = get(self.client.emojis, name='DeutscheBahn')
            await ctx.message.add_reaction(emoji)
            logger.info(f"resume")
        await ctx.message.delete(delay=10)

    @commands.command(name='skip')
    @check_role()
    async def _skip(self, ctx: commands.Context):
        vc = ctx.voice_client
        if vc.is_playing():
            vc.stop()
            logger.info(f"skip")
        await ctx.message.delete(delay=10)

    @commands.command(name='stop')
    @check_role()
    async def _stop(self, ctx):
        """Stops the playing or paused song."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            logger.warning("nothing to stop")
            return await ctx.send('Ich Spiele grade nichts', delete_after=20)
        vc.stop()
        emoji = get(self.client.emojis, name='SaltyCaptin')
        logger.info(f"stop")
        await ctx.message.add_reaction(emoji)
        await self.cleanup(ctx.guild)
        await ctx.message.delete(delay=10)

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player


def setup(client):
    client.add_cog(PlaySounds(client))
