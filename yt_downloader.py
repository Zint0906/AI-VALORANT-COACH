import yt_dlp
import asyncio

def _download_sync(url: str, output_path: str):
    """동기적으로 유튜브 영상을 다운로드합니다 (무료 서버 용량 한계를 위해 720p 최적화)"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

async def download_youtube_video(url: str, output_path: str):
    """디스코드 비동기 루프가 멈추지 않도록 별도 스레드에서 다운로드 실행"""
    await asyncio.to_thread(_download_sync, url, output_path)
