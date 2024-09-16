import discord  # discord 모듈을 import
from discord.ext import commands
import yt_dlp as youtube_dl  # yt-dlp를 youtube_dl로 사용
from youtubesearchpython import VideosSearch  # YouTube 검색 기능

# 봇 기본 설정 (이전과 동일)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# yt-dlp 설정 (이전과 동일)
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

# FFmpeg 경로를 설정 (C:\ffmpeg\bin\ffmpeg.exe 경로를 사용)
ffmpeg_path = 'C:/ffmpeg/bin/ffmpeg.exe'  # 경로를 직접 지정

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
        # FFmpeg 경로를 지정하여 호출
        return cls(discord.FFmpegPCMAudio(filename, executable=ffmpeg_path, **ffmpeg_options), data=data)

# YouTube 검색 기능 수정
def search_youtube(query):
    search = VideosSearch(query, limit=1)  # 검색 결과를 1개만 가져옴
    results = search.result()
    if results and 'result' in results:
        video = results['result'][0]  # 첫 번째 검색 결과 가져오기
        return video['link']  # 유튜브 링크 반환
    return None

# 봇 명령어 및 이벤트 설정 (이전과 동일)
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
        url = search_youtube(search)  # 유튜브에서 곡 검색
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

# 봇 토큰 추가
bot.run('')
