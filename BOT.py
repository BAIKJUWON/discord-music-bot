import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from youtube_search import YoutubeSearch  # youtube-search-python 사용

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# yt-dlp 설정
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'noplaylist': True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ffmpeg_path = '/usr/bin/ffmpeg'  # Docker에서 FFmpeg 경로

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, executable=ffmpeg_path, **ffmpeg_options), data=data)

# YouTube 검색 기능
def search_youtube(query):
    search = YoutubeSearch(query, max_results=1)
    results = search.to_dict()
    if results and len(results['videos']) > 0:
        video = results['videos'][0]  # 첫 번째 비디오 검색 결과 선택
        video_link = f"https://www.youtube.com/watch?v={video['id']}"
        return video_link
    return None

# 봇 명령어 설정
@bot.command(name='join', help='음성 채널에 봇을 참여시킵니다.')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("음성 채널에 먼저 들어가세요!")
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name='leave', help='봇을 음성 채널에서 나가게 합니다.')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("봇이 음성 채널에 없습니다.")

@bot.command(name='play', help='입력한 곡 제목으로 YouTube에서 음악을 재생합니다.')
async def play(ctx, *, search: str):
    async with ctx.typing():
        url = search_youtube(search)
        if url is None:
            await ctx.send(f"'{search}'에 대한 검색 결과를 찾을 수 없습니다.")
            return

        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Error: {e}') if e else None)

    await ctx.send(f"지금 재생 중: {player.title}")

@bot.command(name='stop', help='재생 중인 음악을 멈춥니다.')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("현재 재생 중인 음악이 없습니다.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# 봇 실행
bot.run('key')
