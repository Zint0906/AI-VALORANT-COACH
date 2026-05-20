import os
import time
import asyncio
import google.generativeai as genai
from prompts import COACH_PROMPT

def configure_gemini():
    """Gemini API 설정 초기화"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)

def _process_video_sync(file_path: str) -> str:
    """Gemini 클라우드 업로드, 처리 대기 및 결과 반환"""
    video_file = None
    try:
        print(f"[{file_path}] Gemini 서버로 영상 파일 전송 중...")
        video_file = genai.upload_file(path=file_path)
        
        print(f"[{file_path}] Gemini 내부 영상 인코딩 대기 중...")
        while video_file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
            
        if video_file.state.name == "FAILED":
            raise Exception("Gemini 서버에서 영상 처리를 실패했습니다.")
            
        print(f"\n[{file_path}] 인코딩 완료. 3.1 flash lite 모델 호출 분석 시작...")
        
        # 멀티모달 영상 분석용 1.5 Pro 필수 사용
        model = genai.GenerativeModel(model_name="gemini-3.1-flash-lite")
        response = model.generate_content(
            [video_file, COACH_PROMPT],
            request_options={"timeout": 600}
        )
        
        return response.text

    finally:
        # 클라우드 용량 관리를 위해 분석 완료 직후 원격 임시 파일 완전 소거
        if video_file:
            print(f"[{file_path}] Gemini 클라우드 임시 파일 정리 중...")
            try:
                genai.delete_file(video_file.name)
            except Exception as e:
                print(f"원격 파일 삭제 실패: {e}")

async def analyze_valorant_video(file_path: str) -> str:
    """비동기 래퍼 함수"""
    configure_gemini()
    return await asyncio.to_thread(_process_video_sync, file_path)
