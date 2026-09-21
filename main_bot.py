# pip install discord.py
# pip install "discord.py[voice]" yt-dlp PyNaCl

# Windows
# winget install Gyan.FFmpeg

# Linux
# sudo apt install -y ffmpeg

import discord, os, sys, yt_dlp, asyncio
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# 인텐트(권한) 설정
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

# 뻘짓
def error(text):
    return "[+] 에러!\n" + text
def success(text):
    return "[+] 성공!\n" + text

# 상태 저장 딕셔너리
user_online_time = {} # 누적 온라인 초
user_login_time = {} # 온라인된 시각
user_game_total = {} # 누적 게임 시간
user_current_game = {} # 게임시간 임시저장

# 서버 아이디
server_id = 1546128396524847106

# 토큰 불러오기
def get_token():
    file_name = "Token.txt" # 토큰 파일 이름
    dir = os.path.dirname(os.path.abspath(__file__))
    dir = os.path.join(dir, file_name)
    if not os.path.exists(dir): # 파일 없을 때
        print(error(f"[+] 파일 읽기 실패!\n[+] \"{file_name}\" 파일을 생성해주세요!"))
        sys.exit(1) # 프로그램 종료

    with open(dir, "r", encoding="utf=8") as f:
        token = f.read().strip()
    print(success(f"[+] 파일을 찾았습니다!"))

    if not token: # 파일 비었을 때
        print(error(f"[+] 파일이 비어있습니다!"))
        sys.exit(1)

    return token

# 봇 객체 생성
BOT = commands.Bot(command_prefix="!", intents=intents)

# yt-dlp, FFmpeg 기본 옵션
YDL_OPTIONS = {
    'format': 'm4a/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=1.0"'
}

# '간고등어'
ijun = 1547935249885962381 # 고유 아이디 보려면 프로필 우클릭하고 맨 아래 "사용자 ID 복사하기"
def IsIjun(userid):
    if userid == ijun:
        return True
    else:
        return False

# 게임 감지 함수
def get_playing_game_name(member):
    for activity in member.activities:
        if isinstance(activity, discord.Game):
            return activity.name
        elif activity.type == discord.ActivityType.playing:
            return activity.name
    return None

# 봇 이벤트
@BOT.event
async def on_ready():
    print(success(f"[+] 로그인: {BOT.user.name} (ID: {BOT.user.id})"))
    
    # 슬래시 커맨드 동기화
    try:
        guild = discord.Object(id=server_id)
        BOT.tree.copy_global_to(guild=guild)
        synced = await BOT.tree.sync(guild=guild)
        print(success(f"[+] 슬래시 커맨드 {len(synced)}개 동기화 완료"))
    except Exception as e:
        print(error(f"[+] 동기화 에러: {e}"))

    # 봇 켜진 시점에 이미 서버에 접속해 있는 유저 및 게임 일괄 등록
    now = datetime.now()
    server = BOT.get_guild(server_id)
    
    if server:
        online_count = 0
        game_count = 0
        for member in server.members:
            if member.bot:
                continue

            # 온라인/자리비움/다른용무중인 유저 등록
            if member.status != discord.Status.offline:
                user_login_time[member.id] = now
                online_count += 1

            # 이미 게임 켜고 있는 유저 등록
            game_name = get_playing_game_name(member)
            if game_name:
                user_current_game[member.id] = {
                    "game_name": game_name,
                    "start_time": now
                }
                game_count += 1

        print(success(f"[+] 기존 접속자 {online_count}명, 게임 플레이어 {game_count}명 시간 추적 시작!"))

# 유저 상태 및 게임 변화 감지 이벤트
@BOT.event
async def on_presence_update(before, after):
    if after.bot:
        return

    old_status = before.status
    new_status = after.status

    # 접속시간
    # 접속중
    if new_status != discord.Status.offline and after.id not in user_login_time:
        user_login_time[after.id] = datetime.now()
        print(f"[+] {after.display_name} 접속 감지 시작! ({new_status})")

    # 오프라인
    elif new_status == discord.Status.offline and after.id in user_login_time:
        login_time = user_login_time.pop(after.id)
        duration = (datetime.now() - login_time).total_seconds()
        user_online_time[after.id] = user_online_time.get(after.id, 0) + duration
        print(f"[-] {after.display_name} 접속 종료! (약 {int(duration / 60)}분 머뭄)")

    # 게임시간
    old_game = get_playing_game_name(before)
    new_game = get_playing_game_name(after)

    if old_game != new_game:
        # 이전 게임 종료 누적
        if old_game is not None:
            user_info = user_current_game.pop(after.id, None)
            if user_info and user_info["game_name"] == old_game:
                duration = (datetime.now() - user_info["start_time"]).total_seconds()
                if after.id not in user_game_total:
                    user_game_total[after.id] = {}
                user_game_total[after.id][old_game] = user_game_total[after.id].get(old_game, 0) + duration
                print(f"[-] {after.display_name}가 '{old_game}' 종료 (플레이: {int(duration / 60)}분)")

        # 새 게임 시작
        if new_game is not None:
            user_current_game[after.id] = {
                "game_name": new_game,
                "start_time": datetime.now()
            }
            print(f"[+] {after.display_name}가 '{new_game}' 플레이 시작!")

# 도움!
DoUm = "# 명령어들\
        \n\n## 채팅\
        \n* **!도움** or **/도움**\
        \n `도움말을 출력한다.`\
        \n* **!간고등어**\
        \n `멍청이`\
        \n* **!멍청이**\
        \n `간고등어를 부른다.`\
        \n* **!안녕**\
        \n `인사한다.`\
        \n* **!ping**\
        \n `핑(지연시간)을 확인한다.`\
        \n* **!say**\
        \n `반복해서 말한다. !say 치면 자세한 사용법 나온다.`\
        \n\n## 노래관련\
        \n* **!노래사용법**\
        \n `여기에 '!노래' 시리즈 설명하기 귀찮으니깐 이거치면 설명한다.`\
        \n* **!노래재생**\
        \n `노래를 재생한다.`\
        \n* **!노래일시정지**\
        \n `노래를 일시정지한다.`\
        \n* **!노래다시재생**\
        \n `노래를 다시 재생한다.`\
        \n* **!노래퇴장**\
        \n `봇을 퇴장시킨다.`\
        \n\n## 접속관련\
        \n* **!접속시간**\
        \n `접속한 시간을 알려준다.`\
        \n* **!게임시간**\
        \n `게임을 한 시간을 알려준다.`\
        \n\n## 주의할점\
        \n* **거의 모든 명령어는 앞에 `!`를 붙인다.**\
        \n* **딱히없다. 그냥 잘 쓰면 된다.**\
        \n* **큰따옴표(\") 있으면 붙여라.**"

NoreDoUm = "# 노래 재생 방법!\
            \n`!노래재생 \"{노래 제목}\"` : `노래 제목`을 재생한다.\
            \n\n## 노래 멈추고 다시 재생하는 방법!\
            \n`!노래일시정지` : 노래를 일시정지 시킨다.\
            \n`!노래다시재생` : 노래를 다시 재생시킨다.\
            \n# 봇 퇴장시키는 방법!\
            \n`!노래퇴장` : 봇을 퇴장시킨다.\
            \n\n## **주의할점**\
            \n* 방에 들어가있어야지 봇이 들어가서 재생시킨다.\
            \n* `!노래재생`만 입력하면 재생 안된다. `\"{노래 제목}\"`도 입력해라.\
            \n* `{노래 제목}`에는 꼭 `\"`(큰따옴표)사이에 넣어라.\
            \n* `{노래 제목}` 대신 URL을 넣으면 정확한 곡을 재생시킬 수 있다!"

# 슬래시 명령어

# 도움
@BOT.tree.command(name="도움", description="도움! 명령어를 모르겠음!")
async def helpSlash(interaction: discord.Interaction):
    await interaction.response.send_message(DoUm)

# 느낌표명령어


# 채팅
# 도움
@BOT.command(name="도움", description="도움! 명령어를 모르겠음!")
async def helpPoint(ctx):
    await ctx.send(DoUm)

# 이준바보
@BOT.command(name="간고등어", description="멍청이")
async def IjunBaBo(ctx):
    await ctx.send("멍@청@이")

# 멍청이
@BOT.command(name="멍청이", description="이@준")
async def BaBoIjun(ctx):
    await ctx.send(f"# <@{ijun}>")

# 안녕
@BOT.command(name="안녕", description="간고등어를 부른다.")
async def hello(ctx):
    if IsIjun(ctx.author.id):
        await ctx.reply(f"어쩌라고 {ctx.author.mention}")
    else:
        await ctx.reply(f"안녕 간고등어의 친구 {ctx.author.mention}")

# ping
@BOT.command(name="ping", description="핑(지연시간) 확인")
async def ping(ctx):
    latency = round(BOT.latency * 1000)
    await ctx.reply(f"현재 ping은 {latency}ms です")

# say
@BOT.command(name="say", description="반복해서 말한다")
async def say(ctx, text: str, count: int):
    if count < 1:
        text1 = "# 1번 이상 입력해."
    elif count > 100:
        text1 = "# 도배 방지를 위해 최대 100번까지 가능하다."

    res = f"{text}\n" * count

    if len(res) > 2000:
        await ctx.reply("출력 내용이 너무 길다.\n2000자 넘으면 안된다.")
        return

    await ctx.send(res)

@say.error
async def say_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!say {말할거} {몇번할지}` 형식으로 작성.")
    else:
        print(error(f"[+] 알 수 없는 에러!\n{err}"))

# 접속시간
@BOT.command(name="접속시간", description="접속시간을 출력한다.")
async def check_online_status(ctx, member: discord.Member):
    target = member

    status_kr = {
        discord.Status.online: "온라인",
        discord.Status.idle: "자리 비움",
        discord.Status.dnd: "다른 용무 중",
        discord.Status.offline: "오프라인"
    }
    current_status = status_kr.get(target.status, "알 수 없음")

    # 대상이 현재 온라인인데 접속 시작 기록이 없으면 지금부터 카운트 시작
    if target.status != discord.Status.offline and target.id not in user_login_time:
        user_login_time[target.id] = datetime.now()

    # 누적 초 계산
    total_seconds = user_online_time.get(target.id, 0)
    if target.id in user_login_time:
        total_seconds += (datetime.now() - user_login_time[target.id]).total_seconds()

    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    await ctx.reply(
        f"# **{target.display_name}**(이)의 현재 상태: {current_status}\n"
        f"총 `{hours}시간 {minutes}분 {seconds}초`동안 접속"
    )

@check_online_status.error
async def check_online_status_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!접속시간 {유저맨션}` 형식으로 작성.")
    else:
        print(error(f"[+] 알 수 없는 에러!\n{err}"))

# 게임시간
@BOT.command(name="게임시간", description="게임시간을 출력한다.")
async def check_game_time(ctx, member: discord.Member):
    target = member

    records = dict(user_game_total.get(target.id, {}))

    if target.id in user_current_game:
        current = user_current_game[target.id]
        cur_name = current["game_name"]
        cur_stay = (datetime.now() - current["start_time"]).total_seconds()
        records[cur_name] = records.get(cur_name, 0) + cur_stay

    if not records:
        await ctx.reply(f"## **{target.display_name}**(이)는 게임을 하지 않았다!")
        return

    text_list = []
    sorted_records = sorted(records.items(), key=lambda x: x[1], reverse=True)

    for game_name, total_seconds in sorted_records:
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        is_now = ""
        if target.id in user_current_game and user_current_game[target.id]["game_name"] == game_name:
            is_now = "**지금 플레이중**"

        text_list.append(f"**{game_name}** : {hours}시간 {minutes}분 {seconds}초")

    result_text = "\n".join(text_list)
    await ctx.reply(f"# **{target.display_name}**(이)의 오늘의 게임 시간\n{result_text}")

@check_game_time.error
async def check_game_time_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!게임시간 {유저맨션}` 형식으로 작성.")
    else:
        print(error(f"[+] 알 수 없는 에러!\n{err}"))


# 음성
# 노래사용법
@BOT.command(name="노래사용법", description="노래 사용법을 출력한다.")
async def HowtoUsePlayTheSong(ctx):
    await ctx.reply(NoreDoUm)

# 재생
@BOT.command(name="노래재생", description="노래를 재생한다.")
async def play(ctx, search: str):
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return

    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client

    # 봇이 음성채널에 없으면 입장
    try:
        ctx.voice_client.pause() # 먼저 재생중이던 노래 멈추고 입장
    except:
        pass
    if not voice_client:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    # 유튜브에서 음원 or URL 추출
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        if not search.startswith("http"):
            await ctx.send("음원 검색중이다...")
            search = f"ytsearch:{search}" # 검색어로 찾기
        else:
            await ctx.send("음원을 재생하겠다...")
        info = ydl.extract_info(search, download=False) # URL로 찾기
        if 'entries' in info:
            info = info['entries'][0]
        url = info['url']
        title = info.get('title', '제목 없음')

    # 재생 중이면 중지 후 새로 재생
    if voice_client.is_playing():
        voice_client.stop()

    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
    voice_client.play(source)

    await ctx.reply(f"**재생 시작!**\n{title}")

@play.error
async def play_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!노래재생 \"{노래 제목}\"` 형식으로 작성.")
    else:
        print(error(f"[+] 알 수 없는 에러!\n{err}"))


# 일시정지
@BOT.command(name="노래일시정지", description="노래를 정지시킨다.")
async def pause(ctx):
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.reply("ザ・ワールド！時よ止まれ！")

# 다시 재생
@BOT.command(name="노래다시재생", description="정지시킨 노래를 다시 재생시킨다.")
async def resume(ctx):
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.reply("そして、　時は動き出す。。。")

# 퇴장
@BOT.command(name="노래퇴장", description="노래를 재생하는 봇을 퇴장시킨다.")
async def leave(ctx):
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.reply("퇴장!")
    else:
        await ctx.reply("퇴장 불가능!")

TOKEN = get_token()
BOT.run(TOKEN)