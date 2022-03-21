import asyncio

from async_timeout import timeout
from config import DISCORD


class MusicPlayer:
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = DISCORD['volume']
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(100):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            audio_source = source.to_audio_source()
            audio_source.volume = self.volume
            self.current = audio_source

            # print(self._guild.voice_client)

            self._guild.voice_client.play(audio_source,
                                          after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            await self._channel.send(embed=source.to_embed(), delete_after=30)  # self.np =
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            audio_source.cleanup()
            self.current = None

            # try:
            #     #We are no longer playing this song...
            #    await self.np.delete()
            # except discord.HTTPException:
            #    pass

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))
