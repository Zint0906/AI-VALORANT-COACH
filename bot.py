import discord
import os
import uuid
import re
import asyncio
from dotenv import load_dotenv
from gemini_client import analyze_valorant_video
from yt_downloader import download_youtube_video

# Render 웹 서비스 구동을 위한 FastAPI 및 ASGI 서버 라이브러리
from fastapi import FastAPI
import uvicorn

# 1. 환경변수 로드 (.env 파일은 로컬 테스트용, Render는 대시보드 등록 방식)
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 2. 인스턴스 초기화
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
app = FastAPI()

YT_REGEX = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'

# Render 웹 서버 생존 확인(Health Check)용 엔드포인트
@app.get("/")
def read_root():
    return {"status": "healthy", "bot": "Valorant AI Coach"}

def split_message(text: str, limit: int = 1900):
    """디스코드 메시지 글자 수 제한(2000자) 우회용 세이프 스플리터"""
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
    print(f'🎮 Render 웹 서비스 모드로 구동 중입니다.')
    print(f'======================================')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # 채팅 메시지 내 유튜브 링크 감지
    yt_match = re.search(YT_REGEX, message.content)
    if yt_match:
        youtube_url = yt_match.group(0)
        await handle_coaching_request(message, youtube_url)

async def handle_coaching_request(message: discord.Message, url: str):
    """다운로드 및 분석 메인 파이프라인"""
    file_id = str(uuid.uuid4())[:8]
    local_file_path = f"temp_vod_{file_id}.mp4"
    
    status_msg = await message.reply("🎯 **[AI Coach]** 유튜브 링크가 확인되었습니다! 분석용 원본 영상을 추출합니다...")
    
    try:
        # 1. 유튜브 백그라운드 다운로드
        await download_youtube_video(url, local_file_path)
        await status_msg.edit(content="🎥 영상 추출 완료! AI 코치가 타임라인 정밀 분석을 시작합니다.\n*(Render 무료 플랜 특성상 최종 리포트 출력까지 약 2~4분이 소요됩니다.)*")
        
        # 2. Gemini 멀티모달 피드백 생성
        feedback = await analyze_valorant_video(local_file_path)
        
        # 3. 안전하게 가공된 피드백 순차 전송
        await status_msg.edit(content="📋 **분석이 모두 완료되었습니다! 코치 리포트를 전달합니다.**")
        
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
        
    finally:
        # Render 인스턴스의 디스크 용량 과부하 방지를 위해 로컬 임시 파일 완전 제거
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
            print(f"로컬 임시 파일 삭제 완료: {local_file_path}")

# 3. 포트 바인딩 및 동시 비동기 루프 실행 설정
async def main():
    # Render가 동적으로 열어주는 내부 웹 포트 수신 (없으면 기본 8000 사용)
    port = int(os.environ.get("PORT", 8000))
    
    # 0.0.0.0 외부 바인딩 설정을 주어야 Render가 포트 스캔 타임아웃 에러를 안 냅니다.
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # 웹서비스와 디스코드 봇을 동시에 단일 프로세스에서 비동기로 병렬 처리
    await asyncio.gather(
        server.serve(),
        client.start(TOKEN)
    )

if __name__ == '__main__':
    if not TOKEN and not os.environ.get("DISCORD_BOT_TOKEN"):
        print("❌ 실행 실패: DISCORD_BOT_TOKEN 환경 변수가 유실되었습니다.")
    else:
        asyncio.run(main())
