import os
import google.generativeai as genai
from prompts import COACH_PROMPT

def configure_gemini():
    """Gemini API 설정 초기화"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)

async def analyze_valorant_video(video_url_or_path: str) -> str:
    """
    [우회 최적화] 
    만약 입력값이 유튜브 링크라면 직접 다운로드하지 않고, 
    Gemini 가 원격으로 유튜브 내용을 파싱하도록 링크를 그대로 전달합니다.
    """
    configure_gemini()
    
    # 멀티모달 영상 분석용 1.5 Pro 모델 호출
    model = genai.GenerativeModel(model_name="gemini-3.1-flash-lite")
    
    # 문자열이 웹 주소(http)인 경우: 다운로드 없이 주소와 프롬프트를 결합해 즉시 제미나이에 전달
    if video_url_or_path.startswith("http"):
        print(f"🔗 [Gemini Remote] 유튜브 링크 직접 분석 모드 가동: {video_url_or_path}")
        
        full_prompt = f"""
        아래의 유튜브 VOD 링크 영상을 직접 시청하고 분석해줘.
        영상 링크: {video_url_or_path}
        
        {COACH_PROMPT}
        """
        
        # 외부 스레드 차단 방지를 위해 비동기 처리
        import asyncio
        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt,
            request_options={"timeout": 600}
        )
        return response.text
        
    else:
        # 일반 로컬 파일 경로인 경우 (기존 로직 유지)
        import time
        video_file = genai.upload_file(path=video_url_or_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
            
        response = model.generate_content([video_file, COACH_PROMPT], request_options={"timeout": 600})
        try:
            genai.delete_file(video_file.name)
        except:
            pass
        return response.text
