# pip install discord.py
# pip install "discord.py[voice]" yt-dlp PyNaCl

# Windows
# winget install Gyan.FFmpeg

# Linux
# sudo apt install -y ffmpeg

import discord, os, sys, yt_dlp, asyncio, json
from discord import app_commands
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from datetime import datetime, time, timezone, timedelta

# 인텐트(권한) 설정
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

# 한국시간 정의
KST = timezone(timedelta(hours=9)) # 표준시간에서 한국시간 오차 빼기

# 뻘짓
def error(text):
    return "[+] 에러!\n" + text
def success(text):
    return "[+] 성공!\n" + text

# 노래
SongList = [] # 리스트
Infinite = False # 무한재생

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
        print(error(f"[+] Token 파일 읽기 실패!\n[+] \"{file_name}\" 파일을 생성해주세요!"))
        sys.exit(1) # 프로그램 종료

    with open(dir, "r", encoding="utf=8") as f:
        token = f.read().strip()
    print(success(f"[+] Token 파일을 찾았습니다!"))

    if not token: # 파일 비었을 때
        print(error(f"[+] Token 파일이 비어있습니다!"))
        sys.exit(1)

    return token

# 시간 저장 파일 저장하기
def save_time_data():
    file_name = "user_time_data.json" # 시간 저장 파일 이름
    dir = os.path.dirname(os.path.abspath(__file__))
    dir = os.path.join(dir, file_name)

    now = datetime.now()

    # 현재 접속중인 유저 정산
    for user_id in list(user_login_time.keys()):
        duration = (now - user_login_time[user_id]).total_seconds()
        user_online_time[user_id] = user_online_time.get(user_id, 0) + duration
        user_login_time[user_id] = now # 시작 기준시간 초기화

    # 현재 게임중인 유저 정산
    for user_id, current in list(user_current_game.items()):
        game_name = current["game_name"]
        duration = (now - current["start_time"]).total_seconds()
        if user_id not in user_game_total:
            user_game_total[user_id] = {}
        user_game_total[user_id][game_name] = user_game_total[user_id].get(game_name, 0) + duration
        current["start_time"] = now # 시작 기준시간 초기화

    data = {"online_time": user_online_time,
            "game_total": user_game_total}
    with open(dir, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(success(f"[+] JSON 저장 성공!"))

# 시간 저장 파일 불러오기
def load_time_data():
    file_name = "user_time_data.json" # 시간 저장 파일 이름
    dir = os.path.dirname(os.path.abspath(__file__))
    dir = os.path.join(dir, file_name)
    global user_online_time, user_game_total
    if os.path.exists(dir):
        try:
            with open(dir, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_online_time = {int(k): v for k, v in data.get("online_time", {}).items()}
                user_game_total = {int(k): v for k, v in data.get("game_total", {}).items()}
            print(success(f"[+] JSON 불러오기 성공!"))
        except Exception as e:
            print(error(f"[+] JSON 불러오기 실패!\n{e}"))

# 봇 객체 생성
BOT = commands.Bot(command_prefix="!", intents=intents)

# yt-dlp, FFmpeg 기본 옵션
YDL_OPTIONS = {
    'format': 'm4a/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'remote_components': ['ejs:github']
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

# 시간 초기화
@tasks.loop(time=time(hour=0, minute=0, second=0, tzinfo=KST))
async def reset_status():
    now = datetime.now()

    user_online_time.clear()
    user_game_total.clear()

    for user_id in list(user_login_time.keys()):
        user_login_time[user_id] = now

    for user_id in list(user_current_game.keys()):
        user_current_game[user_id]["start_time"] = now

    save_time_data()

    print(success(f"[+] {now.strftime('%Y-%m-%d')} - 시간 초기화!"))

@tasks.loop(seconds=30)
async def auto_save():
    save_time_data()

# 봇 이벤트
@BOT.event
async def on_ready():
    load_time_data()
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

    if not reset_status.is_running():
        reset_status.start()
    if not auto_save.is_running():
        auto_save.start()

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
        \n `반복해서 말한다.`\
        \n* **!시간**\
        \n `현재 시간을 출력한다.`\
        \n\n## 노래관련\
        \n* **!노래사용법**\
        \n `여기에 '!노래' 시리즈 설명하기 귀찮으니깐 이거치면 설명한다.`\
        \n* **!노래재생**\
        \n `노래를 재생한다.`\
        \n* **!노래추가**\
        \n `다음 노래를 설정한다.`\
        \n* **!노래확인**\
        \n `노래들을 확인한다.`\
        \n* **!노래스킵**\
        \n `다음 노래로 넘어간다.`\
        \n* **!노래삭제**\
        \n `노래를 삭제한다.`\
        \n* **!노래리셋**\
        \n `리스트에 있는 노래들을 모두 삭제한다.`\
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
        \n\n## 도움말\
        \n* `--help를 명려어 뒤에 붙여서 사용법을 출력한다.`\
        \n\n## 주의할점\
        \n* **거의 모든 명령어는 앞에 `!`를 붙인다.**\
        \n* **딱히없다. 그냥 잘 쓰면 된다.**\
        \n* **큰따옴표(\") 있으면 붙여라.**"

NoreDoUm = "# 노래 재생 방법!\
            \n`!노래재생 \"{노래 제목}\"` : `노래 제목`을 재생한다.\
            \n`!노래재생 \"{노래 제목}\" -R` : `노래 제목`을 죽을때까지 재생한다.\
            \n\n## 노래 멈추고 다시 재생하는 방법!\
            \n`!노래일시정지` : 노래를 일시정지 시킨다.\
            \n`!노래다시재생` : 노래를 다시 재생시킨다.\
            \n\n## 다음노래 시리즈 사용방법!\
            \n`!노래추가 \"{노래 제목}\" {N!}` : 노래 리스트 가장 마지막에 `노래 제목`을 추가한다.\n{N1}에 번호를 입력하면 해당 위치에 추가한다.\
            \n`!노래확인` : 노래들을 리스트로 확인한다.\
            \n`!노래스킵` : 이번 노래를 스킵하고 다음 노래로 넘어간다.\
            \n`!노래삭제 {N1}` : 리스트의 `N1`번째 노래를 삭제한다.\
            \n`!노래리셋` : 리스트에 있는 노래들을 모두 삭제한다.\
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

def ishelp(param): # --help가 포함됬는지
    return "--help" in param


# 채팅
# 도움
@BOT.command(name="도움", description="도움! 명령어를 모르겠음!")
async def helpPoint(ctx, *, param: str = ""):
    if ishelp(param):
        await ctx.reply("도움말에 도움말이 필요할까...?")
        return
    await ctx.send(DoUm)

# 이준바보
@BOT.command(name="간고등어", description="멍청이")
async def IjunBaBo(ctx, * , param: str = ""):
    if ishelp(param):
        await ctx.reply("간고등어는 멍청이다.")
        return
    await ctx.send("멍@청@이")

# 멍청이
@BOT.command(name="멍청이", description="이@준")
async def BaBoIjun(ctx, *, param: str = ""):
    if ishelp(param):
        await ctx.reply("간고등어를 부른다.")
        return
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
        await ctx.reply("# 1번 이상 입력해.")
        return
    elif count > 100:
        await ctx.reply("# 도배 방지를 위해 최대 100번까지 가능하다.")
        return

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

@BOT.command(name="시간", description="시간을 출력한다.")
async def printTime(ctx):
    await ctx.reply(f"{datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}")

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
        f"오늘 `{hours}시간 {minutes}분 {seconds}초`동안 접속"
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

# 노래 끝났을 때 다음 곡 자동 재생 콜백
def on_song_end(ctx, voice_client, err=None):
    global SongList, Infinite
    if err:
        print(error(f"[+] 재생 에러!\n{err}"))
        return
    if not voice_client or not voice_client.is_connected():
        return

    if not Infinite:
        if SongList:
            SongList.pop(0) # 다 끝난 현재 곡(0번) 제거

    if SongList:
        source = discord.FFmpegPCMAudio(SongList[0]['url'], **FFMPEG_OPTIONS)
        voice_client.play(source, after=lambda e: on_song_end(ctx, voice_client, e))
        if not Infinite:
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"**다음 노래 재생!**\n{SongList[0]['title']}"),
                BOT.loop
            )
    else:
        Infinite = False

# 재생
@BOT.command(name="노래재생", description="노래를 재생한다.")
async def play(ctx, search: str, param1: str = None):
    global SongList, Infinite
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return

    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client

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

    SongList.clear()
    Infinite = False

    # 기존 재생 중이던 곡이 있다면 정지
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    # 리스트 맨 앞에 바로 재생할 곡 삽입 (기존 재생곡이 있다면 덮어쓰기)
    SongList.append({"title": title, "url": url})
    Infinite = (param1 in ("-R", "-r"))


    source = discord.FFmpegPCMAudio(SongList[0]['url'], **FFMPEG_OPTIONS)
    voice_client.play(source, after=lambda e: on_song_end(ctx, voice_client, e))

    if Infinite:
        await ctx.reply(f"**무한재생 시작!**\n{SongList[0]['title']}")
    else:
        await ctx.reply(f"**재생 시작!**\n{SongList[0]['title']}")

@play.error
async def play_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!노래재생 \"{노래 제목}\"` 형식으로 작성.")
    else:
        print(error(f"[+] 알 수 없는 에러!\n{err}"))

# 다음 노래 추가
@BOT.command(name="노래추가", description="노래를 추가한다.")
async def add_song(ctx, search: str, index: int = None):
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        if not search.startswith("http"):
            await ctx.send("음원 검색중이다...")
            search = f"ytsearch:{search}"
        else:
            await ctx.send("음원을 추가하겠다...")
        info = ydl.extract_info(search, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        url = info['url']
        title = info.get('title', '제목 없음')

    song_data = {"title": title, "url": url}

    if index is None:
        SongList.append(song_data)
        await ctx.reply(f"**노래 추가 완료! ({len(SongList)}번)**\n{title}")
    elif index == 1:
        SongList.insert(1, song_data)
        await ctx.reply(f"**Index Range Error!!!**\n## 다음 곡으로 추가했습니다. (2번)\n{title}")
    elif index < 2 or index > len(SongList) + 1:
        SongList.append(song_data)
        await ctx.reply(f"**Index Range Error!!!**\n## 가장 뒤에 곡을 추가했습니다. ({len(SongList)}번)\n{title}")
    else:
        SongList.insert(index - 1, song_data)
        await ctx.reply(f"**노래 추가 완료! ({index}번)**\n{title}")

@add_song.error
async def add_song_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!노래추가 \"{노래 제목}\"` 형식으로 작성.")
    else:
        print(error(f"[+] 알 수 없는 에러!\n{err}"))

# 노래확인
@BOT.command(name="노래확인", description="노래 리스트를 확인한다.")
async def check_song(ctx):
    if not SongList:
        await ctx.reply("노래 리스트가 비어있다.")
        return
    songlist = "# 노래 리스트!\n"
    for i in range(len(SongList)):
        if i == 0:
            songlist += f"## 1\. {SongList[i]['title']} (재생중이다.)\n"
        else:
            songlist += f"{i+1}\. {SongList[i]['title']}\n"
    await ctx.reply(songlist)

# 노래스킵
@BOT.command(name="노래스킵", description="다음 노래로 넘어간다.")
async def skip_song(ctx):
    global Infinite
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        Infinite = False # 스킵할 땐 무한재생 해제
        if len(SongList) <= 1:
            await ctx.reply("다음 노래가 없다. 끈다.")
        ctx.voice_client.stop() # stop() 호출 시 on_song_end가 자동 실행되어 pop(0) 후 다음 곡 재생!

# 노래리셋
@BOT.command(name="노래리셋", description="노래 리스트를 초기화한다.")
async def reset_song(ctx):
    global SongList, Infinite
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    SongList.clear()
    Infinite = False
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        ctx.voice_client.stop()
    await ctx.reply("노래 리스트를 초기화했다.")

# 노래삭제
@BOT.command(name="노래삭제", description="노래를 삭제한다.")
async def delete_song(ctx, index: int):
    global SongList, Infinite
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if not SongList:
        await ctx.reply("삭제할 노래가 없다.")
        return
    if index < 1 or index > len(SongList):
        await ctx.reply(f"1번부터 {len(SongList)}번 사이로 입력해라.")
        return

    if index == 1:
        # 1번은 현재 재생중인 곡이므로 스킵과 동일하게 처리
        deleted_title = SongList[0]['title']
        Infinite = False
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
        else:
            SongList.pop(0)
        await ctx.reply(f"**1\. {deleted_title}** (현재 재생곡) 삭제 완료!")
    else:
        deleted_song = SongList.pop(index - 1)
        await ctx.reply(f"**{index}\. {deleted_song['title']}** 삭제 완료!")

@delete_song.error
async def delete_song_error(ctx, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.reply("# 사용법\n`!노래삭제 {N1}` 형식으로 작성.")
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
        await ctx.reply("そして、 時は動き出す。。。")

# 퇴장
@BOT.command(name="노래퇴장", description="노래를 재생하는 봇을 퇴장시킨다.")
async def leave(ctx):
    global SongList, Infinite
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.reply("퇴장!")
        SongList.clear()
        Infinite = False
    else:
        await ctx.reply("퇴장 불가능!")

# 나가
@BOT.command(name="나가", description="노래를 재생하는 봇을 퇴장시킨다.")
async def leave_naga(ctx):
    global SongList, Infinite
    if not ctx.author.voice:
        await ctx.reply("음성 채널에 들어가라.")
        return
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.reply("퇴장!")
        SongList.clear()
        Infinite = False
    else:
        pass

TOKEN = get_token()
BOT.run(TOKEN)