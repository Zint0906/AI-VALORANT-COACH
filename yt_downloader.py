import yt_dlp
import asyncio

def _download_sync(url: str, output_path: str):
    """쿠키 없이 브라우저/앱 변장 옵션으로 유튜브 차단을 우회합니다."""
    ydl_opts = {
        # 용량 관리를 위해 720p 이하 최적화
        'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        
        # [핵심 우회 옵션] 실제 일반 크롬 브라우저 환경인 것처럼 변장합니다.
        'impersonate': 'chrome', 
        
        # 유튜브 서버에 요청할 때 웹 브라우저 대신 안드로이드 앱 클라이언트인 척 속입니다.
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['dash', 'hls']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

async def download_youtube_video(url: str, output_path: str):
    await asyncio.to_thread(_download_sync, url, output_path)
