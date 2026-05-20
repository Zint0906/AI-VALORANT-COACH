import discord
import os
import uuid
import re
import asyncio
from dotenv import load_dotenv
from gemini_client import analyze_valorant_video
from yt_downloader import download_youtube_video

from fastapi import FastAPI
import uvicorn

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
app = FastAPI()

# 명령어 접두사 설정 (예: !코칭)
COMMAND_PREFIX = "!코칭"
YT_REGEX = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'

@app.get("/")
def read_root():
    return {"status": "healthy", "bot": "Valorant AI Coach"}

def split_message(text: str, limit: int = 1900):
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
    print(f'🎮 !코칭 명령어를 받을 준비가 되었습니다.')
    print(f'======================================')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # 메시지가 '!코칭'으로 시작하는지 확인
    if message.content.startswith(COMMAND_PREFIX):
        # '!코칭' 뒤에 붙은 유튜브 링크 추출
        yt_match = re.search(YT_REGEX, message.content)
        
        if yt_match:
            youtube_url = yt_match.group(0)
            await handle_coaching_request(message, youtube_url)
        else:
            # 명령어는 쳤는데 링크를 안 올렸거나 잘못 올린 경우 안내
            await message.reply("❌ **[사용법]** `!코칭 [유튜브 영상 링크]` 형태로 입력해 주세요!\n(예시: `!코칭 https://youtu.be/...`)")

async def handle_coaching_request(message: discord.Message, url: str):
    file_id = str(uuid.uuid4())[:8]
    local_file_path = f"temp_vod_{file_id}.mp4"
    
    status_msg = await message.reply("🎯 **[AI Coach]** 분석 요청을 접수했습니다. 영상을 추출하고 있으니 잠시만 기다려 주세요...")
    
    try:
        await download_youtube_video(url, local_file_path)
        await status_msg.edit(content="🎥 영상 추출 완료! AI 코치가 정밀 분석을 시작합니다.\n*(리포트 작성까지 약 2~4분이 소요됩니다.)*")
        
        feedback = await analyze_valorant_video(local_file_path)
        await status_msg.edit(content="📋 **분석이 모두 완료되었습니다! 코치 리포트를 전달합니다.**")
        
        chunks = split_message(feedback)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)
                
    except Exception as e:
        await status_msg.edit(content=f"❌ 코칭 도중 예외 에러가 발생했습니다.\n`사유: {str(e)}`")
        print(f"Error log: {e}")
        
    finally:
        if os.path.exists(local_file_path):
            os.remove(local_file_path)

async def main():
    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        client.start(TOKEN)
    )

if __name__ == '__main__':
    if not TOKEN and not os.environ.get("DISCORD_BOT_TOKEN"):
        print("❌ DISCORD_BOT_TOKEN이 유실되었습니다.")
    else:
        asyncio.run(main())
