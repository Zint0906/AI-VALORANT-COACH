import discord
import os
import uuid
import re
import asyncio
from dotenv import load_dotenv
from gemini_client import analyze_valorant_video

# Render 웹 서비스 포트 바인딩용 라이브러리
from fastapi import FastAPI
import uvicorn

# 1. 환경변수 로드 (.env 또는 Render 대시보드 변수)
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 2. 디스코드 봇 및 FastAPI 웹 서버 초기화
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
app = FastAPI()

COMMAND_PREFIX = "!코칭"
# 모든 형태의 웹 주소(유튜브, 쇼츠 등)를 감지하는 정규식
URL_REGEX = r'https?://[^\s]+'

# Render 생존 확인(Health Check)용 기본 페이지
@app.get("/")
def read_root():
    return {"status": "healthy", "bot": "Valorant AI Coach (Direct Link Mode)"}

def split_message(text: str, limit: int = 1900):
    """디스코드 2000자 글자 수 제한 우회용 세이프 스플리터"""
    chunks = []
    lines = text.split('\n')
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > limit:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

@client.event
async def on_ready():
    print(f'======================================')
    print(f'✅ 디스코드 봇 로그인 성공: {client.user.name}')
    print(f'🎮 다이렉트 링크 전송 모드로 구동 중입니다. (!코칭)')
    print(f'======================================')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # 유저가 '!코칭'으로 메시지를 시작했는지 확인
    if message.content.startswith(COMMAND_PREFIX):
        url_match = re.search(URL_REGEX, message.content)
        
        if url_match:
            video_url = url_match.group(0)
            await handle_coaching_request(message, video_url)
        else:
            # 주소를 같이 안 적었을 때 안내 멘트
            await message.reply("❌ **[사용법]** `!코칭 [유튜브 영상 링크]` 형태로 입력해 주세요!\n(예시: `!코칭 https://youtu.be/...`)")

async def handle_coaching_request(message: discord.Message, url: str):
    """유튜브를 다운로드하지 않고 Gemini 서버에 링크만 토스하는 핵심 파이프라인"""
    status_msg = await message.reply("🎯 **[AI Coach]** 분석 요청이 접수되었습니다. Gemini AI 서버로 직접 링크를 전송하는 중...")
    
    try:
        # [🔥 차단 우회] yt-dlp 다운로드를 거치지 않고, 수정한 gemini_client로 링크를 바로 토스합니다.
        feedback = await analyze_valorant_video(url)
        
        await status_msg.edit(content="📋 **분석이 모두 완료되었습니다! 코치 리포트를 전달합니다.**")
        
        # 안전하게 가공된 피드백을 디스코드에 순차 전송
        chunks = split_message(feedback)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)
                
    except Exception as e:
        error_msg = f"❌ 코칭 도중 예외 에러가 발생했습니다.\n`사유: {str(e)}`"
        await status_msg.edit(content=error_msg)
        print(f"Error log: {e}")

async def main():
    # Render가 주는 동적 포트 수신
    port = int(os.environ.get("PORT", 8000))
    
    # 0.0.0.0 외부 개방 설정을 주어야 Render가 포트 스캔 에러를 내지 않습니다.
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # 웹 서버와 디스코드 봇을 동시에 실행
    await asyncio.gather(
        server.serve(),
        client.start(TOKEN)
    )

if __name__ == '__main__':
    if not TOKEN and not os.environ.get("DISCORD_BOT_TOKEN"):
        print("❌ DISCORD_BOT_TOKEN이 유실되었습니다.")
    else:
        asyncio.run(main())
