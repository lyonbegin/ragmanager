"""
기존 코드 완전 포함 + 구조 개선 버전
모든 LLM 호출, 파싱, 프롬프트 로직 보존
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import uuid
import re
import os
import time
import requests
from datetime import datetime
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from db import BotDatabase
import html
from flask_socketio import SocketIO, emit, join_room
import threading
# ============================================
# 기존 전역 변수 및 설정 (그대로 유지)
# ============================================

from pathlib import Path
app = Flask(__name__)


CORS(app)


socketio = SocketIO(app, cors_allowed_origins="*")

room_users = {}
# bot_db = None

# LLM 서버 설정 (기존)
HF_TOKEN = os.getenv('HF_TOKEN', "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")
MODEL_ID = "openai/gpt-oss-20b"
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', "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")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
HOST_IP = "localhost"
LLM_SERVER_URL = f"http://{HOST_IP}:11700/chatbot"

# Hugging Face Client 초기화 (기존)
try:
    from huggingface_hub import InferenceClient
    client = InferenceClient(provider="hyperbolic", api_key=HF_TOKEN)
    print(f"✅ Hugging Face Inference Client 초기화 성공. Model: {MODEL_ID}")
except Exception as e:
    print(f"🚨 FATAL ERROR: Hugging Face Inference Client 초기화 실패: {e}")
    exit(1)

# Mock 데이터 (기존)
MOCK_DATA_BATCH = {
    "type": "test_batch",
    "items": [
        # ==========================================
        # 1. 기본 메시지 유형 (Basic Message Types)
        # ==========================================
        {
            "type": "text",
            "content": "📢 [기본 유형 테스트] 먼저 일반 메시지 타입들을 보여드립니다."
        },
        {
            "type": "image",
            "sender": "Bot",
            "images": [
                "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=400&q=80",
                "https://images.unsplash.com/photo-1498804103079-a6351b050096?w=400&q=80"
            ]
        },
        {
            "type": "checklist",
            "checklistTitle": "여행 필수 준비물",
            "checklistItems": [
                {"label": "여권 챙기기 (유효기간 확인)", "checked": True},
                {"label": "포켓 와이파이 예약", "checked": False},
                {"label": "110v 돼지코 변환기", "checked": False}
            ]
        },
        {
            "type": "link",
            "linkData": {
                "title": "오사카 맛집 지도 (구글맵)",
                "desc": "현지인이 추천하는 숨은 맛집 리스트를 확인하세요.",
                "thumb": "https://images.unsplash.com/photo-1569388330292-79cc1ec67270?w=400",
                "url": "https://maps.google.com/..."
            }
        },
        {
            "type": "location",
            "locationData": {
                "name": "인천국제공항 제1여객터미널",
                "address": "인천광역시 중구 공항로 272",
                "mapImg": "https://images.unsplash.com/photo-1569336415962-a4bd9f69cd83?w=600&h=300&fit=crop" # 지도 이미지 대용
            }
        },
        {
            "type": "file",
            "fileData": {
                "fileName": "2025_여행_일정표_최종.pdf",
                "size": "2.4 MB",
                "type": "pdf"
            }
        },

        # ==========================================
        # 2. 고급 위젯 유형 (Rich Widgets)
        # ==========================================
        {
            "type": "text",
            "content": "⬇️ 여기부터는 고급 선택형 위젯입니다."
        },
        # 위젯 1: 히어로 카드
        {
            "type": "widget",
            "message": "1. 히어로 카드 (메인 상품)",
            "widget_type": "hero_card_select",
            "content": {
                "title": "오사카 프리미엄 패스",
                "desc": "유니버설 스튜디오 + 주유패스 결합 상품",
                "image": "https://images.unsplash.com/photo-1524820197278-540916411e20?w=600&q=80"
            },
            "options": ["구매하기", "상세보기"]
        },
        # 위젯 2: 캐러셀
        {
            "type": "widget",
            "message": "2. 캐러셀 (쇼핑몰 스타일)",
            "widget_type": "carousel_select",
            "items": [
                {"title": "나이키 에어", "desc": "129,000원", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400"},
                {"title": "아디다스 런", "desc": "89,000원", "image": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=400"},
                {"title": "뉴발란스", "desc": "109,000원", "image": "https://images.unsplash.com/photo-1539185441755-769473a23570?w=400"}
            ]
        },
        # 위젯 3: 이미지 그리드
        {
            "type": "widget",
            "message": "3. 이미지 그리드 (선호도 조사)",
            "widget_type": "image_grid_select",
            "items": [
                {"label": "모던", "image": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=300"},
                {"label": "빈티지", "image": "https://images.unsplash.com/photo-1507089947368-19c1da9775ae?w=300"},
                {"label": "북유럽", "image": "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=300"},
                {"label": "미니멀", "image": "https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?w=300"}
            ]
        },
        # 위젯 4: 비디오 프리뷰
        {
            "type": "widget",
            "message": "4. 비디오 프리뷰 (영상 가이드)",
            "widget_type": "video_preview_select",
            "content": {
                "video_url": "https://www.youtube.com/embed/ScMzIvxBSi4",
                "desc": "이 영상을 보고 미션을 수행해주세요."
            },
            "options": ["영상 시청 완료"]
        },
        # 위젯 5: 리스트 아이템
        {
            "type": "widget",
            "message": "5. 리스트 아이템 (옵션 선택)000000000000000",
            "widget_type": "list_item_select",
            "items": [
                {"title": "감자튀김 추가", "desc": "+2,000원", "image": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=100"},
                {"title": "콜라 변경", "desc": "+500원", "image": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=100"}
            ]
        },
       
        {
            "type": "widget",
            "message": "6. 아바타 선택 (상담원 연결)",
            "widget_type": "avatar_bubble_select",
            "items": [
                {"title": "김상담", "image": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"},
                {"title": "이친절", "image": "https://api.dicebear.com/7.x/avataaars/svg?seed=Aneka"},
                {"title": "박전문", "image": "https://api.dicebear.com/7.x/avataaars/svg?seed=John"}
            ]
        }


    ]
}


def remove_json_codeblocks(text: str) -> str:
    """
    ✅ 새 함수: JSON 코드블록 제거
    
    예:
```json
    { "store_id": "STORE_001" }
```
    <bot_response>...</bot_response>
    
    →
    
    <bot_response>...</bot_response>
    """
    # 1. ```json ... ``` 블록 제거
    text = re.sub(r'```json\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    
    # 2. 단독 {...} JSON 객체 제거 (XML 태그 밖에 있는 것만)
    text = re.sub(r'^\s*\{[^<]*?\}\s*\n', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # 3. 여러 줄 공백 정리
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    return text.strip()


def convert_history_to_single_user_message(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    히스토리를 하나의 user 메시지로 변환 (Hyperbolic 전용)
    
    변환 전:
    [system, user, assistant, user, assistant, user]
    
    변환 후:
    [system, user(모든 대화 히스토리 포함)]
    """
    print(f"\n🔄 [convert_history_to_single_user_message] 시작")
    print(f"   입력: {len(messages)}개 메시지")
    
    if not messages:
        return []
    
    # System 메시지 분리
    system_msg = None
    conversation_msgs = []
    
    print(f"\n📋 메시지 분류:")
    for i, msg in enumerate(messages):
        if msg['role'] == 'system':
            system_msg = msg
            content_preview = msg['content']
            print(f"   [System {i}] {len(msg['content'])} chars")
            print(f"      Preview: {content_preview}...")
            print(f"      🔥 마지막 system으로 저장 (덮어씀)")
        else:
            conversation_msgs.append(msg)
            print(f"   [Other {i}] {msg['role']}: {len(msg['content'])} chars")
    
    print(f"\n📊 분류 결과:")
    print(f"   System 메시지: {'있음' if system_msg else '없음'}")
    if system_msg:
        print(f"      → 최종 system: {len(system_msg['content'])} chars")
    print(f"   대화 메시지: {len(conversation_msgs)}개")
    
    if not conversation_msgs:
        print(f"\n⚠️  대화 메시지 없음 → system만 반환")
        return [system_msg] if system_msg else []
    
    # 🔥 마지막이 user인지 확인
    if conversation_msgs[-1]['role'] != 'user':
        print(f"\n⚠️  [Warning] 마지막 메시지가 user가 아님: {conversation_msgs[-1]['role']}")
        return [system_msg] if system_msg else []
    
    # 모든 대화를 하나의 텍스트로 합치기
    combined_history = []
    
    print(f"\n🔄 대화 히스토리 병합:")
    for i, msg in enumerate(conversation_msgs[:-1]):  # 마지막 user 메시지 제외
        if msg['role'] == 'user':
            combined_history.append(f"사용자: {msg['content']}")
            print(f"   [{i}] 사용자: {len(msg['content'])} chars")
        elif msg['role'] == 'assistant':
            combined_history.append(f"어시스턴트: {msg['content']}")
            print(f"   [{i}] 어시스턴트: {len(msg['content'])} chars")
    
    # 마지막 user 메시지 (현재 입력)
    last_user_msg = conversation_msgs[-1]['content']
    print(f"   [마지막] 현재 사용자 입력: {len(last_user_msg)} chars")
    
    # 히스토리 + 현재 메시지 합치기
    if combined_history:
        full_user_message = "\n\n".join(combined_history) + f"\n\n사용자: {last_user_msg}"
    else:
        full_user_message = last_user_msg
    
    print(f"\n📊 [Hyperbolic Format] 히스토리 변환:")
    print(f"   원본: {len(messages)}개 메시지")
    print(f"   대화 턴: {len(conversation_msgs)}개")
    print(f"   변환: {2 if system_msg else 1}개 메시지 (system + user)")
    print(f"   최종 User 메시지 길이: {len(full_user_message)} chars")
    
    # 최종 메시지
    result = []
    if system_msg:
        result.append(system_msg)
        print(f"\n✅ 최종 System 메시지: {len(system_msg['content'])} chars")
        content_preview = system_msg['content'][:200].replace('\n', ' ')
        print(f"   Preview: {content_preview}...")
    
    result.append({
        'role': 'user',
        'content': full_user_message
    })
    print(f"✅ 최종 User 메시지: {len(full_user_message)} chars")
    
    return result
def remove_duplicate_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    1. 완전 중복 제거
    2. Hyperbolic 형식으로 변환 (system + user 2개만)
    """
    print(f"\n{'🔍'*30}")
    print(f"🔍 [remove_duplicate_messages] 시작")
    print(f"{'🔍'*30}")
    print(f"📥 입력 메시지: {len(messages)}개\n")
    
    if not messages:
        return []
    
    # 🔥 입력 메시지 상세 출력
    for i, msg in enumerate(messages):
        role = msg['role']
        content_preview = msg['content']
        # print(f"[입력 {i}] {role}: {len(msg['content'])} chars")
        print(f"   Preview: {content_preview}...")
        print()
    
    # 1단계: 완전 중복 제거
    print(f"\n{'─'*60}")
    print(f"1️⃣ 완전 중복 제거")
    print(f"{'─'*60}")
    
    unique_messages = []
    for i, msg in enumerate(messages):
        if unique_messages and \
           unique_messages[-1]['role'] == msg['role'] and \
           unique_messages[-1]['content'] == msg['content']:
            print(f"🗑️  [제거] 메시지 {i}: {msg['role']} (완전 중복)")
            continue
        unique_messages.append(msg.copy())
        print(f"✅ [유지] 메시지 {i}: {msg['role']} ({len(msg['content'])} chars)")
    
    if len(messages) != len(unique_messages):
        print(f"\n✅ 중복 제거 결과: {len(messages)}개 → {len(unique_messages)}개")
    else:
        print(f"\n📝 중복 없음: {len(unique_messages)}개 유지")
    
    # 🔥 중복 제거 후 메시지 출력
    print(f"\n{'─'*60}")
    print(f"📤 중복 제거 후 메시지:")
    print(f"{'─'*60}")
    for i, msg in enumerate(unique_messages):
        content_preview = msg['content']
        print(f"[중복제거 {i}] {msg['role']}: {len(msg['content'])} chars")
        print(f"   Preview: {content_preview}...")
        print()
    
    # 2단계: Hyperbolic 형식으로 변환
    print(f"\n{'─'*60}")
    print(f"2️⃣ Hyperbolic 형식 변환")
    print(f"{'─'*60}")
    
    hyperbolic_messages = convert_history_to_single_user_message(unique_messages)
    
    # 🔥 Hyperbolic 변환 후 메시지 출력
    print(f"\n{'─'*60}")
    print(f"📤 Hyperbolic 변환 후 메시지:")
    print(f"{'─'*60}")
    for i, msg in enumerate(hyperbolic_messages):
        content_preview = msg['content']
        print(f"[Hyperbolic {i}] {msg['role']}: {len(msg['content'])} chars")
        print(f"   Preview: {content_preview}...")
        print()
    
    # 3단계: 최종 결과 출력
    print(f"\n{'='*60}")
    print(f"[최종 Hyperbolic 형식]")
    print(f"{'='*60}")
    for i, msg in enumerate(hyperbolic_messages):
        content_preview = msg['content']
        print(f"  [{i}] {msg['role']}: {len(msg['content'])} chars")
        print(f"      Preview: {content_preview}...")
    print(f"{'='*60}\n")
    
    return hyperbolic_messages

def send_llm_request_xml(
    messages: List[Dict[str, str]],
    botjob: bool = False,
    use_hf: bool = True,
    use_openrouter: bool = False
) -> str:
    """
    XML 기반 LLM 요청 (Tool 파라미터 제거)
    
    ⚠️ 모든 LLM 제공자에 XML 강제 지침 적용
    """
    
    # ✅ 1. 공통: XML 강제 지침을 모든 시스템 메시지에 추가


    if botjob :
        xml_enforcement=""


    enhanced_messages = remove_duplicate_messages(messages)



    # 🆕 시스템 프롬프트 미리보기 (공통)
    system_msg = next((m for m in enhanced_messages if m['role'] == 'system'), None)
    if system_msg:
        first_line = system_msg['content'][:100].replace('\n', ' ')
        print(f"📝 [System Prompt Preview] {first_line}...")
    
    # ✅ 2. OpenRouter API 사용
    if use_openrouter:
        model_name = "openai/gpt-4o-mini"
        print(f"📤 [LLM Request] (OpenRouter) 모델: {model_name}, 메시지: {len(enhanced_messages)}개")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": enhanced_messages  # ✅ XML 강제된 메시지 사용
        }

        try:
            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=600)
            
            if response.status_code == 200:
                res_json = response.json()
                content = res_json.get('choices', [{}])[0].get('message', {}).get('content', '')
                if not content:
                    content = res_json.get('content', '')
                
                # ✅ JSON 코드블록 제거
                content = remove_json_codeblocks(content)
                return content
            else:
                return f"Error (OpenRouter): {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Request Failed (OpenRouter): {e}"

    # ✅ 3. Hugging Face 클라이언트 사용
    elif use_hf:
        print(f"📤 [LLM Request] (Hugging Face) 메시지: {len(enhanced_messages)}개")
        
        # 🔥 추가: 메시지 구조 상세 출력
        print(f"\n{'='*60}")
        print(f"📋 [HF Request Details]")
        print(f"{'='*60}")
        for i, msg in enumerate(enhanced_messages):
            role = msg['role']
            content_preview = msg['content'].replace('\n', ' ')
            print(f"[{i}] Role: {role}")
            print(f"    Content: {content_preview}...")
            print(f"    Length: {len(msg['content'])} chars")
        print(f"{'='*60}\n")
        
        try:
            print(f"⏳ [HF] API 호출 중...")
            response = client.chat_completion(
                model=MODEL_ID,

                # provider="hyperbolic",
                messages=enhanced_messages,
                max_tokens=50000
            )
            
            # 🔥 추가: 응답 객체 상세 출력
            print(f"\n{'='*60}")
            print(f"📥 [HF Response Details]")
            print(f"{'='*60}")
            print(f"Response object type: {type(response)}")
            print(f"Has 'choices' attr: {hasattr(response, 'choices')}")
            
            if hasattr(response, 'choices'):
                print(f"Choices count: {len(response.choices)}")
                
                if response.choices:
                    choice = response.choices[0]
                    print(f"Choice[0] type: {type(choice)}")
                    print(f"Has 'message' attr: {hasattr(choice, 'message')}")
                    
                    if hasattr(choice, 'message'):
                        message = choice.message
                        print(f"Message type: {type(message)}")
                        print(f"Has 'content' attr: {hasattr(message, 'content')}")
                        
                        if hasattr(message, 'content'):
                            content = message.content
                            print(f"Content type: {type(content)}")
                            print(f"Content value: {repr(content)}")  # 🔥 None이면 여기서 확인
                            print(f"Content length: {len(content) if content else 0}")
                            
                            if content:
                                print(f"Content preview: {content}")
                        else:
                            print(f"❌ message.content 속성 없음")
                    else:
                        print(f"❌ choice.message 속성 없음")
                else:
                    print(f"❌ choices 리스트 비어있음")
            else:
                print(f"❌ response.choices 속성 없음")
                print(f"Response dir: {dir(response)}")
            
            print(f"{'='*60}\n")
            
            # 기존 로직
            content = response.choices[0].message.content
            
            # ✅ JSON 코드블록 제거
            if not  botjob :
                content = remove_json_codeblocks(content)
            
            print(f"   ✅ Hugging Face 응답: {len(content)} chars")
            return content
            
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ Hugging Face LLM 호출 중 예외 발생")
            print(f"{'='*60}")
            print(f"Exception type: {type(e)}")
            print(f"Exception message: {str(e)}")
            
            import traceback
            print(f"\n전체 스택 트레이스:")
            traceback.print_exc()
            print(f"{'='*60}\n")
            
            return f"LLM 호출 실패: {e}"

    # ✅ 4. 기존 HTTP POST 요청 사용 (Gemini 등)
    else:
        payload = {
            "messages": enhanced_messages,  # ✅ XML 강제된 메시지 사용
            "model": "gemini-2.5-flash-lite",
            "session": ""
        }

        print(f"📤 [LLM Request] (HTTP POST) 메시지: {len(enhanced_messages)}개")
        try:
            response = requests.post(LLM_SERVER_URL, json=payload, timeout=600)
            
            if response.status_code == 200:
                res_json = response.json()
                content = res_json.get('choices', [{}])[0].get('message', {}).get('content', '')
                if not content:
                    content = res_json.get('content', '') 
                
                # ✅ JSON 코드블록 제거
                content = remove_json_codeblocks(content)
                return content
            else:
                return f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Request Failed: {e}"

@dataclass
class ParsedAction:
    """파싱된 액션 데이터"""
    type: str
    data: Dict[str, Any]
    raw_xml: str

class XMLAutoFixer:
    """XML 자동 수정 유틸리티"""
    
    def __init__(self):
        self.self_closing_tags = {'br', 'hr', 'img', 'input', 'meta', 'link'}
    
    def fix_json_wrapped_xml(self, json_str: str) -> str:
        """JSON으로 래핑된 XML 추출 및 수정"""
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and 'bot_response' in data:
                return self.auto_fix_xml(data['bot_response'])
        except json.JSONDecodeError:
            pass
        
        # JSON 파싱 실패시 직접 추출
        match = re.search(r'"bot_response"\s*:\s*"(.+)"', json_str, re.DOTALL)
        if match:
            xml_content = match.group(1)
            xml_content = xml_content.replace('\\"', '"')
            xml_content = xml_content.replace('\\\\', '\\')
            return self.auto_fix_xml(xml_content)
        
        return json_str
    
    def auto_fix_xml(self, response: str) -> str:
        """XML 자동 수정 메인 로직"""
        original = response
        fixes = []
        
        # 1. 루트 태그 추가
        if not re.search(r'^\s*<bot_response', response.strip()):
            response = f"<bot_response>{response}</bot_response>"
            fixes.append("루트 태그")
        
        # 2. HTML 엔티티 디코딩
        response = html.unescape(response)
        
        # 3. 메시지 내용 CDATA 처리
        def wrap_message(match):
            content = match.group(1)
            if '<![CDATA[' in content:
                return match.group(0)
            if any(c in content for c in ['<', '>', '&', '"', "'"]):
                return f"<message><![CDATA[{content}]]></message>"
            return match.group(0)
        
        response = re.sub(r'<message>(.*?)</message>', wrap_message, response, flags=re.DOTALL)
        
        # 4. action 속성 이스케이프 제거
        backslash_quote = '\\"'
        response = re.sub(
            r'<action\s+([^>]+)>',
            lambda m: "<action {}>".format(m.group(1).replace(backslash_quote, '"')),
            response
        )

        
                
        # 5. JSON value를 CDATA로 감싸기
        def wrap_value(match):
            content = match.group(1)
            if content.strip().startswith(('[', '{')):
                return f"<value><![CDATA[{content}]]></value>"
            return match.group(0)
        
        response = re.sub(r'<value>(.*?)</value>', wrap_value, response, flags=re.DOTALL)
        
        # 6. 이스케이프 시퀀스 정리
        response = response.replace('\\n', '\n').replace('\\t', '\t')
        
        # 7. 닫히지 않은 태그 자동 닫기
        tag_stack = []
        for match in re.finditer(r'<(/?)(\w+)(?:\s+[^>]*)?(/?)>', response):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2)
            is_self_closing = match.group(3) == '/' or tag_name in self.self_closing_tags
            
            if is_closing:
                if tag_stack and tag_stack[-1] == tag_name:
                    tag_stack.pop()
            elif not is_self_closing:
                tag_stack.append(tag_name)
        
        if tag_stack:
            for tag in reversed(tag_stack):
                response += f"</{tag}>"
                fixes.append(f"</{tag}>")
        
        if fixes:
            print(f"   🔧 XML 자동 수정: {', '.join(fixes)}")
        
        return response
    
    def validate_xml(self, xml_str: str) -> tuple[bool, Optional[str]]:
        """XML 유효성 검사"""
        try:
            ET.fromstring(xml_str)
            return True, None
        except Exception as e:
            return False, str(e)

class XMLToolParser:
    """XML 기반 Tool 응답 파싱"""
    
    def __init__(self):
        self.parsing_levels = [
            self._parse_full_xml,
            self._parse_regex_actions,
            self._parse_loose_tags,
            self._parse_keywords
        ]

        self.xml_fixer = XMLAutoFixer()
    
    def parse(self, llm_response: str) -> Tuple[str, List[ParsedAction]]:
        """
        LLM 응답을 파싱
        
        Returns:
            (natural_message, actions)
        """
        print(f"\n🔍 [XML Parser] 응답 길이: {len(llm_response)} chars")

         # 🆕 추가: 응답 미리보기
        preview = llm_response[:150].replace('\n', ' ')
        print(f"   미리보기: {preview}...")
        
        # 자동 수정 시도
        # fixed_response = self.auto_fix_xml(llm_response)


        if llm_response.strip().startswith('{'):
            fixed_response = self.xml_fixer.fix_json_wrapped_xml(llm_response)
        else:
            fixed_response = self.xml_fixer.auto_fix_xml(llm_response)
    
        # 계층적 파싱 시도
        for level, parser_func in enumerate(self.parsing_levels, 1):
            try:
                message, actions = parser_func(fixed_response)
                if message or actions:  # 액션이 하나라도 파싱되면 성공
                    print(f"   ✅ Level {level} 파싱 성공: {len(actions)}개 액션")
                    return message, actions
            except Exception as e:
                print(f"   ⚠️ Level {level} 실패: {e}")
                continue
        
        # 모든 파싱 실패 시 자연어만 추출
        print("   ⚠️ 모든 파싱 레벨 실패 - 자연어만 반환")
        return self._extract_natural_text(llm_response), []
    
    def auto_fix_xml(self, response: str) -> str:
        """XML 자동 수정"""
        original = response
        
        # 1. 루트 태그 추가
        if not re.search(r'<bot_response\b', response):
            response = f"<bot_response>{response}</bot_response>"
        
        # 2. 특수문자 이스케이프 (메시지 내용만)
        def escape_message_content(match):
            content = match.group(1)
            # CDATA로 감싸기
            return f"<message><![CDATA[{content}]]></message>"
        
        response = re.sub(
            r'<message>(.*?)</message>',
            escape_message_content,
            response,
            flags=re.DOTALL
        )
        
        # 3. 닫히지 않은 태그 자동 닫기
        open_tags = re.findall(r'<(\w+)(?:\s+[^>]*)?(?<!/)>', response)
        close_tags = re.findall(r'</(\w+)>', response)
        
        unclosed = []
        for tag in open_tags:
            if tag not in ['br', 'hr', 'img']:  # self-closing 제외
                if open_tags.count(tag) > close_tags.count(tag):
                    unclosed.append(tag)
        
        for tag in reversed(list(dict.fromkeys(unclosed))):  # 중복 제거 + 역순
            response += f"</{tag}>"
            print(f"   🔧 자동 수정: </{tag}> 태그 추가")
        
        if response != original:
            print(f"   ✅ XML 자동 수정 완료")
        
        return response
    
    def _parse_full_xml(self, response: str) -> Tuple[str, List[ParsedAction]]:
        """Level 1: 완전한 XML 파싱"""
        # XML 선언 제거
        response = re.sub(r'<\?xml[^>]+\?>', '', response)
        
        root = ET.fromstring(response)
        
        # 메시지 추출
        message_elem = root.find('.//message')
        message = message_elem.text if message_elem is not None else ""
        
        # 액션 추출
        actions = []
        for action_elem in root.findall('.//action'):
            action_type = action_elem.get('type')
            data = {}
            
            for child in action_elem:
                data[child.tag] = child.text or ""
            
            actions.append(ParsedAction(
                type=action_type,
                data=data,
                raw_xml=ET.tostring(action_elem, encoding='unicode')
            ))
        
        return message, actions
    
    def _parse_regex_actions(self, response: str) -> Tuple[str, List[ParsedAction]]:
        """Level 2: 정규식 기반 파싱 (✅ JSON 파싱 추가)"""
        import json
        
        # 메시지 추출
        message_match = re.search(r'<message>(.*?)</message>', response, re.DOTALL)
        message = message_match.group(1).strip() if message_match else ""
        
        # CDATA 제거
        message = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', message, flags=re.DOTALL)
        
        # 액션 추출
        actions = []
        action_pattern = r'<action\s+type="([^"]+)"[^>]*>(.*?)</action>'
        
        for match in re.finditer(action_pattern, response, re.DOTALL):
            action_type = match.group(1)
            action_content = match.group(2)
            
            data = {}
            
            # 일반 필드 추출
            for tag in ['field', 'subbot_id', 'summary', 'purpose', 'validated', 'reason']:
                tag_match = re.search(f'<{tag}>(.*?)</{tag}>', action_content, re.DOTALL)
                if tag_match:
                    data[tag] = tag_match.group(1).strip()
            
            # ✅ value 필드 특별 처리
            value_match = re.search(r'<value>(.*?)</value>', action_content, re.DOTALL)
            if value_match:
                raw_value = value_match.group(1).strip()
                
                # CDATA 제거
                raw_value = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', raw_value, flags=re.DOTALL)
                
                # JSON 파싱 시도
                if raw_value.startswith('[') or raw_value.startswith('{'):
                    try:
                        parsed_json = json.loads(raw_value)
                        data['value'] = json.dumps(parsed_json, ensure_ascii=False, separators=(',', ':'))
                        print(f"      ✅ JSON 파싱 성공: {len(str(parsed_json))} chars")
                    except json.JSONDecodeError as e:
                        print(f"      ⚠️ JSON 파싱 실패: {str(e)[:50]}")
                        data['value'] = raw_value
                else:
                    data['value'] = raw_value
            
            actions.append(ParsedAction(
                type=action_type,
                data=data,
                raw_xml=match.group(0)
            ))
        
        return message, actions
    def _parse_loose_tags(self, response: str) -> Tuple[str, List[ParsedAction]]:
        """Level 3: 느슨한 태그 매칭 (닫는 태그 없어도 OK)"""
        message = ""
        actions = []
        
        # 메시지 추출 (닫는 태그 없어도)
        message_match = re.search(r'<message>([^<]+)', response)
        if message_match:
            message = message_match.group(1).strip()
        
        # update_data 액션 추출
        update_pattern = r'<action\s+type="update_data"[^>]*>(.*?)(?=<action|</actions>|$)'
        for match in re.finditer(update_pattern, response, re.DOTALL):
            content = match.group(1)
            
            field_match = re.search(r'<field>([^<]+)', content)
            value_match = re.search(r'<value>([^<]+)', content)
            validated_match = re.search(r'<validated>(true|false)', content, re.IGNORECASE)
            
            if field_match and value_match:
                actions.append(ParsedAction(
                    type="update_data",
                    data={
                        'field': field_match.group(1).strip(),
                        'value': value_match.group(1).strip(),
                        'validated': validated_match.group(1).lower() == 'true' if validated_match else True  # ✅ Boolean
                    },
                    raw_xml=match.group(0)
                ))
        
        # complete_task 액션
        if re.search(r'<action\s+type="complete_task"', response):
            summary_match = re.search(r'<summary>([^<]+)', response)
            actions.append(ParsedAction(
                type="complete_task",
                data={'summary': summary_match.group(1) if summary_match else '완료'},
                raw_xml='<action type="complete_task">...</action>'
            ))
        
        # switch_bot 액션
        switch_match = re.search(r'<action\s+type="switch_bot"[^>]*>(.*?)(?=<action|</actions>|$)', response, re.DOTALL)
        if switch_match:
            content = switch_match.group(1)
            target_match = re.search(r'<target>([^<]+)', content)
            reason_match = re.search(r'<reason>([^<]+)', content)
            
            if target_match:
                actions.append(ParsedAction(
                    type="switch_bot",
                    data={
                        'target': target_match.group(1).strip(),
                        'reason': reason_match.group(1).strip() if reason_match else ''
                    },
                    raw_xml=switch_match.group(0)
                ))
        
        return message, actions
    
    def _parse_keywords(self, response: str) -> Tuple[str, List[ParsedAction]]:
        """Level 4: 키워드 기반 추출 (최후의 수단)"""
        actions = []
        
        # ✅ 더 정확한 필드 패턴 (스키마에 정의된 필드만)
        field_patterns = {
            # 쿠폰 발급 관련
            'coupon_issuer_id': r'(?:쿠폰\s*)?발급자?\s*(?:ID|아이디)?[:\s]+([A-Z_0-9]{3,})',
            'discount_rate': r'할인율?[:\s]+(\d+)',
            'store_id': r'(?:매장|가게)\s*(?:ID|아이디)?[:\s]+([A-Z_0-9]{3,})',
            'coupon_user_id': r'사용자?\s*(?:ID|아이디)?[:\s]+([A-Z_0-9]{3,})',
            
            # 수학 문제 관련 (서브봇)
            'question': r'문제[:\s]+(.+?)(?=\n|$)',
            'answer': r'(?:정답|답)[:\s]+(\d+)',
        }
        
        for field, pattern in field_patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                extracted_value = match.group(1).strip()
                
                # ✅ 너무 짧거나 의미 없는 값 필터링
                if len(extracted_value) < 2 or extracted_value in ['ID', 'id', '값', 'value']:
                    print(f"   ⚠️ 잘못된 값 필터링: {field} = '{extracted_value}'")
                    continue
                
                actions.append(ParsedAction(
                    type="update_data",
                    data={
                        'field': field,
                        'value': extracted_value,
                        'validated': True  # ✅ Boolean으로 설정
                    },
                    raw_xml='(키워드 기반 추출)'
                ))
                
                print(f"   🔍 키워드 추출: {field} = {extracted_value}")
        
        return response, actions
    
    def _extract_natural_text(self, response: str) -> str:
        """XML 태그 제거하고 자연어만 추출"""
        # 모든 XML 태그 제거
        text = re.sub(r'<[^>]+>', '', response)
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


# ============================================
# STEP 2: XML 액션 실행기
# ============================================

class XMLActionExecutor:
    """XML 액션 실행 (단순화 버전)"""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager  # ✅ 추가
    
    def execute_actions(
        self,
        actions: List[ParsedAction],
        session: 'SessionStateManager',
        config_manager: 'ConfigManager'
    ) -> Dict[str, Any]:
        """
        액션 실행 및 즉시 처리
        """
        result = {
            'bot_changed': False,
            'data_updated': False,
            'completed': False,
            'target_bot_id': None
        }
        
        for action in actions:
            print(f"🔧 [Action] {action.type}: {action.data}")
            
            if action.type == 'update_data':
                self._handle_update_data(action, session, result)
            
            elif action.type == 'complete_task':
                self._handle_complete_task(action, session, result, config_manager)
            
            elif action.type == 'call_subbot':
                # ✅ 여기서 바로 전환 처리
                self._handle_call_subbot(action, session, result)
            
            # elif action.type == 'switch_bot':
            #     # ✅ 여기서 바로 전환 처리
            #     self._handle_switch_bot(action, session, result)
            
            # elif action.type == 'ask_again':
            #     print(f"   ℹ️ 재질문: {action.data.get('error', '')}")
            
            else:
                print(f"   ⚠️ 알 수 없는 액션: {action.type}")
        
        return result
    
    def _handle_update_data(self, action: ParsedAction, session, result):
        """데이터 업데이트"""
        field = action.data.get('field')
        value = action.data.get('value')
        validated = action.data.get('validated', 'true')
        
        # Boolean/String 처리
        if isinstance(validated, bool):
            validated_bool = validated
        elif isinstance(validated, str):
            validated_bool = validated.lower() == 'true'
        else:
            validated_bool = True
        
        if validated_bool and field and value:
            # 중복 방지
            if field in session.shared_context and session.shared_context[field] == value:
                print(f"   ⏭️ 중복 데이터 건너뛰기: {field}")
                return
            
            session.shared_context[field] = value
            result['data_updated'] = True
            print(f"   ✅ 데이터 저장: {field} = {value}")
        else:
            print(f"   ⚠️ 검증 실패: {action.data.get('reason', 'validated=false')}")
    
    def _handle_complete_task(self, action, session, result, config_manager):
        """작업 완료 처리 (필수 필드 체크 포함)"""
        
        # ✅ 필수 필드 체크
        bot_config = config_manager.get_bot_config(session.get_active_bot())
        must_fill = bot_config.completion_condition.get('must_fill', [])
        
        missing_fields = []
        for field in must_fill:
            value = session.shared_context.get(field)
            # None, 빈 문자열, 'null', 'None' 모두 누락으로 처리
            if value is None or str(value).strip() == '' or str(value) in ['null', 'None']:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ⚠️ 완료 불가: 필수 필드 누락 {missing_fields}")
            
            # ✅ 누락된 필드 정보 가져오기
            missing_info = []
            for field in missing_fields:
                # data_schema에서 필드 정보 찾기
                field_info = None
                for schema in bot_config.data_schema:
                    if schema.get('field_name') == field:
                        field_info = schema
                        break
                
                if field_info:
                    missing_info.append({
                        'field': field,
                        'description': field_info.get('description', field),
                        'prompt': field_info.get('prompt_guide', f"{field}를 입력해주세요")
                    })
          
            # ✅ 첫 번째 누락 필드 요청 메시지 생성
            if missing_info:
                first_missing = missing_info[0]
                ask_message = f"{first_missing['prompt']}"
                
                print(f"   📝 누락 필드 요청: {first_missing['field']}")
                print(f"   💬 메시지: {ask_message}")
                
                # ✅ 히스토리에 추가 (LLM이 다음에 참고)
                session.conversation_history.append({
                    "role": "assistant",
                    "content": ask_message
                })
                
                # ✅ result에 메시지 저장 (클라이언트로 전송)
                result['ask_for_missing'] = True
                result['missing_field_message'] = ask_message
                result['missing_fields'] = missing_fields
            else:
                # schema 정보가 없으면 기본 메시지
                ask_message = f"다음 정보가 필요합니다: {', '.join(missing_fields)}"
                
                session.conversation_history.append({
                    "role": "assistant",
                    "content": ask_message
                })
                
                result['ask_for_missing'] = True
                result['missing_field_message'] = ask_message
                result['missing_fields'] = missing_fields
            
            return  # 완료 안 함!
        
        # ✅ 모든 필드가 채워졌을 때만 완료
        print(f"   ✅ 작업 완료: {action.data.get('summary', '완료')}")
        print(f"   🔒 세션 완료 플래그 설정")
        session.task_completed = True
        result['completed'] = True
        
    def _handle_call_subbot(
        self,
        action: ParsedAction,
        session: 'SessionStateManager',
        result: Dict[str, Any]
    ) -> None:
        """
        서브봇 호출 및 즉시 전환
        """
        subbot_id = action.data.get('subbot_id')

        if not subbot_id:
            print(f"   ⚠️ subbot_id 없음")
            return

        print(f"   🔄 서브봇 전환: {session.get_active_bot()} → {subbot_id}")

        # ✅ 서브봇 실행 이력 기록 (중복 호출 방지)
        from datetime import datetime
        executed_subbots = session.get_metadata('executed_subbots', {})
        current_bot = session.get_active_bot()

        executed_subbots[subbot_id] = {
            'called_from': current_bot,
            'timestamp': datetime.utcnow().isoformat()
        }
        session.set_metadata('executed_subbots', executed_subbots)
        print(f"   📝 서브봇 실행 이력 기록: {subbot_id}")

        # ✅ 즉시 전환
        session.push_bot(subbot_id)

        # ✅ 히스토리 백업 (서브봇은 깨끗한 상태로 시작)
        session._main_bot_history = list(session.conversation_history)
        session.conversation_history = []
        print(f"   🧹 히스토리 백업 완료")

        result['bot_changed'] = True
        result['target_bot_id'] = subbot_id
    
    def _handle_switch_bot(self, action: ParsedAction, session, result):
        """
        봇 전환 및 즉시 처리
        """
        target = action.data.get('target')
        
        if not target:
            print(f"   ⚠️ target 없음")
            return
        
        print(f"   🎯 봇 전환: {session.get_active_bot()} → {target}")
        print(f"      이유: {action.data.get('reason', 'N/A')}")
        
        # ✅ 즉시 전환
        session.push_bot(target)
        
        # ✅ 히스토리 백업
        session._main_bot_history = list(session.conversation_history)
        session.conversation_history = []
        
        result['bot_changed'] = True
        result['target_bot_id'] = target



def _build_subbot_prompt(
    bot_config: 'BotConfig', 
    current_data: Dict[str, Any],
    main_bot_id: str = None
) -> str:
    """
    서브봇 전용 동적 프롬프트 생성
    - generate_subbot_json에서 만든 구조를 그대로 활용
    - llm_execution_guide를 중심으로 프롬프트 생성
    - 메인봇 복귀는 call_subbot으로 처리
    """
    
    import logging
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("🔧 _build_subbot_prompt 시작 (서브봇)")
    print("=" * 80)
    print(f"📌 bot_config.bot_id: {bot_config.bot_id}")
    print(f"📌 bot_config.task_name: {bot_config.task_name}")
    print(f"📌 main_bot_id: {main_bot_id}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ data_schema에서 필드 찾기
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("-" * 80)
    print("1️⃣ data_schema 분석")
    print("-" * 80)
    
    main_field = None
    completion_flag_field = None
    selection_field = None
    
    print(f"📋 data_schema 필드 개수: {len(bot_config.data_schema)}")
    
    for i, field_info in enumerate(bot_config.data_schema):
        field_type = field_info.get('field_type')
        field_name = field_info.get('field_name', 'N/A')
        
        print(f"   [{i}] {field_name} (type: {field_type})")
        
        if field_type == 'subbot_result':
            main_field = field_info
            print(f"      ✅ 메인 필드로 설정")
        elif field_type == 'completion_flag':
            completion_flag_field = field_info
            print(f"      ✅ 완료 플래그로 설정")
        elif field_type == 'selection_result':
            selection_field = field_info
            print(f"      ✅ 선택 필드로 설정")
    
    if not main_field:
        logger.error("❌ subbot_result 필드를 찾을 수 없음!")
        return f"⚠️ 서브봇 설정 오류: subbot_result 필드가 없습니다."
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ 메인 필드 정보 추출 (✅ field_name 우선순위)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("-" * 80)
    print("2️⃣ 메인 필드 정보 추출")
    print("-" * 80)
    
    # ✅ field_name 우선, 없으면 variable_name
    field_name = main_field.get('field_name')
    if not field_name:
        field_name = main_field.get('variable_name')
        print(f"   ℹ️  field_name 없음 → variable_name 사용")
    
    if not field_name:
        logger.error("❌ field_name과 variable_name 모두 없음!")
        return "⚠️ 서브봇 설정 오류: 필드명을 찾을 수 없습니다."
    
    variable_name = main_field.get('variable_name', field_name)
    
    # ✅ description도 여러 경로에서 찾기
    description = main_field.get('description', '')
    if not description:
        description = main_field.get('purpose', '')
    if not description:
        description = field_name
    
    subbot_type = main_field.get('subbot_type', 'direct_return')
    
    print(f"📌 field_name: {field_name}")
    print(f"📌 variable_name: {variable_name}")
    print(f"📌 subbot_type: {subbot_type}")
    print(f"📌 description: {description}")
    
    # ✅ llm_execution_guide는 main_field 또는 bot_config에서
    llm_guide = main_field.get('llm_execution_guide', {})
    if not llm_guide:
        llm_guide = getattr(bot_config, 'llm_execution_guide', {})
    
    print(f"📌 llm_execution_guide 존재: {bool(llm_guide)}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ 현재 데이터 상태 확인 (✅ 시스템 필드 제외)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("-" * 80)
    print("3️⃣ 현재 데이터 상태 확인")
    print("-" * 80)
    
    SYSTEM_FIELDS = {'message', 'room_id', 'user_id', 'timestamp'}
    
    current_value = current_data.get(field_name)
    
    flag_name = completion_flag_field.get('field_name') if completion_flag_field else f"{field_name}_completed"
    flag_value = current_data.get(flag_name)
    
    print(f"📊 {field_name}: {current_value}")
    print(f"📊 {flag_name}: {flag_value}")
    
    # ✅ 이미 채워진 필드 (시스템 필드 제외)
    filled_fields = []
    for k, v in current_data.items():
        if k in SYSTEM_FIELDS or k.endswith('_completed'):
            continue
        if v is not None and str(v).strip():
            filled_fields.append(f"  ✅ {k}: {v}")
    
    filled_info = "\n".join(filled_fields) if filled_fields else "  (없음)"
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4️⃣ 이미 완료된 경우
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("-" * 80)
    print("4️⃣ 완료 여부 체크")
    print("-" * 80)
    
    if flag_value == True or flag_value == 'true':
        print("✅ 이미 완료됨 → 복귀 프롬프트 반환")
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 서브봇: {bot_config.task_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<subbot_info>
  <bot_id>{bot_config.bot_id}</bot_id>
  <task_name>{bot_config.task_name}</task_name>
  <subbot_type>{subbot_type}</subbot_type>
</subbot_info>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 작업 이미 완료됨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<current_status>
  <field>{field_name}</field>
  <status>completed</status>
  <value>{current_value if current_value else '(데이터 있음)'}</value>
</current_status>

**즉시 메인봇으로 복귀하세요:**

<bot_response>
  <message>{description}이(가) 이미 완료되었습니다.

메인 작업으로 돌아가겠습니다.</message>
  <actions>
     <action type="complete_task">
      <summary>{bot_config.bot_id} 완료</summary>
    </action>
    </action>
  </actions>
</bot_response>


⚠️ **CRITICAL - JSON 형식 규칙:**

**반드시 한 줄로 작성하세요!**
- 줄바꿈 금지 ❌
- 들여쓰기 금지 ❌
- 중괄호 이스케이프: `{{` `}}`

**올바른 예시:**
<value>[{{"coupon_id":"CUP001","title":"할인","discount_rate":25,"valid_until":"2025-08-31","min_amount":30000}}]</value>

**잘못된 예시 (줄바꿈):**
<value>
  [{{"coupon_id":"CUP001"}}]
</value>
"""
    
    print("⏳ 아직 완료되지 않음 → subbot_type별 처리")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5️⃣ API 호출 정보 추출
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("-" * 80)
    print("5️⃣ API 호출 정보 추출")
    print("-" * 80)
    
    api_endpoint = getattr(bot_config, 'api_endpoint', '')
    api_detail = llm_guide.get('api_call_detail', {}) if llm_guide else {}
    
    print(f"🌐 api_endpoint: {api_endpoint}")
    print(f"🌐 method: {api_detail.get('method', 'N/A')}")
    print(f"🌐 url: {api_detail.get('url', 'N/A')}")
    
    before_execution = llm_guide.get('before_execution', '') if llm_guide else ''
    on_success = llm_guide.get('on_success', {}) if llm_guide else {}
    on_error = llm_guide.get('on_error', {}) if llm_guide else {}
    return_to_main = llm_guide.get('return_to_main', {}) if llm_guide else {}
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6️⃣ subbot_type별 분기
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("-" * 80)
    print(f"6️⃣ subbot_type 분기: {subbot_type}")
    print("-" * 80)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # A. 즉시 복귀형 (direct_return)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if subbot_type == 'direct_return':
        print("🚀 direct_return 프롬프트 생성")
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 서브봇: {bot_config.task_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<subbot_info>
  <bot_id>{bot_config.bot_id}</bot_id>
  <task_name>{bot_config.task_name}</task_name>
  <subbot_type>direct_return</subbot_type>
  <purpose>{main_field.get('purpose', description)}</purpose>
</subbot_info>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 현재 상태
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<current_field>
  <field>{field_name}</field>
  <type>subbot_result</type>
  <description>{description}</description>
  <status>not_completed</status>
</current_field>

<collected_data>
{filled_info}
</collected_data>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 API 호출 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Method:** {api_detail.get('method', 'GET')}
**URL:** {api_detail.get('url', api_endpoint)}
**예시 호출:** {api_detail.get('example_call', 'N/A')}

**파라미터:**
{_format_parameters(api_detail.get('parameters_from_collected', []), current_data)}

**실행 전 안내:** {before_execution}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 실행 지시
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **CRITICAL: 사용자 입력 없이 즉시 실행!**

**즉시 다음 작업을 수행하세요:**

1. API를 호출하여 데이터 조회
2. 응답을 {field_name}에 저장
3. 사용자에게 결과 출력
4. 즉시 메인봇에 복귀

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 다음 단계 (API 성공 시)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<next_step>
  <type>return_to_main</type>
  <action>메인봇 호출로 복귀</action>
  <main_bot_id>{main_bot_id}</main_bot_id>
  <next_in_main>{return_to_main.get('next_action', '메인봇의 다음 필드 처리')}</next_in_main>
</next_step>

**수집 후 동작:**
{return_to_main.get('next_action', '메인봇으로 복귀하여 다음 필드 처리')}

🔥 **성공 시 즉시 실행할 XML:**
```xml
<bot_response>
  <message>{before_execution}

{on_success.get('format', '결과: {{API_응답_요약}}')}

메인 작업으로 돌아가겠습니다.</message>
  <actions>
    <!-- 1️⃣ API 응답 저장 -->
    <action type="update_data">
      <field>{field_name}</field>
      <value>

[{{API_응답_데이터}}]

></value>
      <validated>true</validated>
    </action>
    
    <!-- 2️⃣ 완료 플래그 설정 -->
    <action type="update_data">
      <field>{flag_name}</field>
      <value>true</value>
      <validated>true</validated>
    </action>
    
    <!-- 3️⃣ 메인봇 호출 (복귀) -->
   
     <action type="complete_task">
      <summary>{bot_config.bot_id} 완료</summary>
    </action>
   
 
</bot_response>
```

⚠️ **액션 순서 설명:**
1. **update_data**: {field_name}에 API 응답 저장
2. **update_data**: {flag_name}을 true로 설정
3. **call_subbot**: 메인봇 ID ({main_bot_id})로 호출
   - 즉시 복귀형이므로 사용자 입력 없이 실행
   - 메인봇으로 자동 복귀하여 다음 필드 처리

🔥 **실패 시 즉시 실행할 XML:**
```xml
<bot_response>
  <message>{on_error.get('message', '작업 중 오류가 발생했습니다')}

메인 작업으로 돌아가겠습니다.</message>
  <actions>
    <!-- 1️⃣ 플래그를 false로 설정 -->
    <action type="update_data">
      <field>{flag_name}</field>
      <value>false</value>
      <validated>true</validated>
      <reason>{{오류_원인}}</reason>
    </action>
    
    <!-- 2️⃣ 메인봇 호출 (복귀) -->
    <action type="complete_task">
      <summary>{bot_config.bot_id} 완료</summary>
    </action>
  </actions>
</bot_response>
```

⚠️ **중요:**
- 사용자 입력을 기다리지 마세요!
- API 호출 후 즉시 메인봇으로 복귀하세요!
- 성공/실패 모두 call_subbot으로 메인봇에 복귀합니다!



⚠️ **CRITICAL - JSON 형식 규칙:**

**반드시 한 줄로 작성하세요!**
- 줄바꿈 금지 ❌
- 들여쓰기 금지 ❌
- 중괄호 이스케이프: `{{` `}}`

**올바른 예시:**
<value>[{{"coupon_id":"CUP001","title":"할인","discount_rate":25,"valid_until":"2025-08-31","min_amount":30000}}]</value>

**잘못된 예시 (줄바꿈):**
<value>
  [{{"coupon_id":"CUP001"}}]
</value>
"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # B. 선택 대기형 (selection_required)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif subbot_type == 'selection_required':
        print("🎯 selection_required 프롬프트 생성")
        print(f"   current_value 존재: {bool(current_value)}")
        
        selection_config = getattr(bot_config, 'selection_config', {})
        if not selection_config:
            selection_config = main_field.get('selection_config', {})
        
        print(f"   selection_config: {bool(selection_config)}")
        
        display_format = on_success.get('display_format', '') if on_success else ''
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # B-1. 아직 목록 조회 전
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if not current_value:
            print("   📋 1단계: 목록 조회 필요")
            
            return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 서브봇: {bot_config.task_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<subbot_info>
  <bot_id>{bot_config.bot_id}</bot_id>
  <task_name>{bot_config.task_name}</task_name>
  <subbot_type>selection_required</subbot_type>
  <purpose>{main_field.get('purpose', description)}</purpose>
</subbot_info>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 현재 상태
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<current_field>
  <field>{field_name}</field>
  <type>subbot_result</type>
  <description>{description}</description>
  <status>목록 조회 필요</status>
</current_field>

<collected_data>
{filled_info}
</collected_data>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 API 호출 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Method:** {api_detail.get('method', 'GET')}
**URL:** {api_detail.get('url', api_endpoint)}
**예시 호출:** {api_detail.get('example_call', 'N/A')}

**파라미터:**
{_format_parameters(api_detail.get('parameters_from_collected', []), current_data)}

**실행 전 안내:** {before_execution}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 실행 지시 (1단계: 목록 조회)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **CRITICAL: 사용자 입력 없이 즉시 실행!**

**즉시 다음 작업을 수행하세요:**

1. API를 호출하여 목록 조회
2. 응답을 {field_name}에 저장
3. 사용자에게 목록 제시 (아래 형식 사용)

**목록 제시 형식:**
{display_format}

**예상 응답 형식:**
{api_detail.get('expected_response', {}).get('format', 'Array of objects')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 다음 단계 (이 응답 후)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<next_step>
  <type>user_selection</type>
  <field>{selection_config.get('selection_variable', 'selected_item')}</field>
  <action>시스템이 자동으로 사용자 입력을 기다립니다</action>
</next_step>

**수집 후 동작:**
사용자가 선택하면 → 2단계(선택 처리)로 자동 진행

🔥 **즉시 실행할 XML:**
```xml
<bot_response>
  <message>{before_execution}

다음과 같은 옵션이 있습니다:

{{API_응답을_형식에_맞게_출력}}

{selection_config.get('selection_prompt', '원하시는 항목을 선택해주세요')}</message>
  <actions>
    <!-- 목록 저장만 (아직 complete 안 함!) -->
    <action type="update_data">
      <field>{field_name}</field>

       <value>
      
[{{API_응답_배열}}]

></value>


   
      <validated>true</validated>
    </action>
  </actions>
</bot_response>
```

⚠️ **중요:**
- call_subbot을 **호출하지 마세요**
- 이 응답 후 시스템이 자동으로 사용자 입력을 기다립니다
- 사용자가 입력하면 자동으로 2단계 프롬프트가 생성됩니다


⚠️ **CRITICAL - JSON 형식 규칙:**

**반드시 한 줄로 작성하세요!**
- 줄바꿈 금지 ❌
- 들여쓰기 금지 ❌
- 중괄호 이스케이프: `{{` `}}`

**올바른 예시:**
<value>[{{"coupon_id":"CUP001","title":"할인","discount_rate":25,"valid_until":"2025-08-31","min_amount":30000}}]</value>

**잘못된 예시 (줄바꿈):**
<value>
  [{{"coupon_id":"CUP001"}}]
</value>
"""
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # B-2. 목록 조회 완료, 선택 대기 중
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        else:
            print("   👤 2단계: 사용자 선택 대기")
            
            if not selection_config:
                logger.error("   ❌ selection_config 없음!")
                return f"⚠️ 오류: selection_config가 없습니다."
            
            selection_var_name = selection_config.get('selection_variable', 'selected_item')
            selection_prompt = selection_config.get('selection_prompt', '')
            selection_validation = selection_config.get('selection_validation', {})
            
            print(f"   selection_variable: {selection_var_name}")
            
            list_count = len(current_value) if isinstance(current_value, list) else '?'
            
            # ✅ 사용자 입력 확인
            user_input = current_data.get('message', '')
            print(f"   사용자 선택 입력: {user_input}")
            
            guide = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 서브봇: {bot_config.task_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<subbot_info>
  <bot_id>{bot_config.bot_id}</bot_id>
  <task_name>{bot_config.task_name}</task_name>
  <subbot_type>selection_required</subbot_type>
</subbot_info>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 현재 상태
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<current_status>
  <field>{field_name}</field>
  <value>목록 조회 완료 ({list_count}개 항목)</value>
  <next_step>사용자 선택 처리</next_step>
</current_status>

<selection_field>
  <field>{selection_var_name}</field>
  <type>selection_result</type>
  <status>대기 중</status>
  <prompt>{selection_prompt}</prompt>
</selection_field>

<collected_data>
{filled_info}
</collected_data>


⚠️ **CRITICAL - JSON 형식 규칙:**

**반드시 한 줄로 작성하세요!**
- 줄바꿈 금지 ❌
- 들여쓰기 금지 ❌
- 중괄호 이스케이프: `{{` `}}`

**올바른 예시:**
<value>[{{"coupon_id":"CUP001","title":"할인","discount_rate":25,"valid_until":"2025-08-31","min_amount":30000}}]</value>

**잘못된 예시 (줄바꿈):**
<value>
  [{{"coupon_id":"CUP001"}}]
</value>
"""
            
            # ✅ 사용자 입력이 있으면 명시
            if user_input:
                guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 사용자 선택 입력
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<user_input>
  <value>{user_input}</value>
  <target_field>{selection_var_name}</target_field>
</user_input>

⚡ **중요: 사용자가 방금 "{user_input}"라고 입력했습니다.**
이 값을 아래 목록에서 매칭하여 선택을 처리하세요.
"""
            
            flexible_matching = selection_validation.get('flexible_matching', {})
            
            guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 실행 지시 (2단계: 선택 처리)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**사용자 입력을 다음과 같이 처리하세요:**

**유연한 매칭:**
- 번호 매칭: {flexible_matching.get('by_number', '숫자로 입력 시')}
- 이름 매칭: {flexible_matching.get('by_name', '이름 포함 시')}
- ID 매칭: {flexible_matching.get('by_id', 'ID 직접 입력 시')}

**검증 규칙:** {selection_validation.get('rule', '')}

**유효 예시:** {', '.join(selection_validation.get('example_valid', []))}
**무효 예시:** {', '.join(selection_validation.get('example_invalid', []))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 다음 단계 (검증 성공 시)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<next_step>
  <type>return_to_main</type>
  <action>메인봇 호출로 복귀</action>
  <main_bot_id>{main_bot_id}</main_bot_id>
</next_step>

**수집 후 동작:**
메인봇으로 복귀 → 메인봇의 다음 필드 자동 처리

🔥 **유효한 선택 시 즉시 응답:**
```xml
<bot_response>
  <message>{{선택된_항목_이름}}을(를) 선택하셨습니다!

메인 작업으로 돌아가겠습니다.</message>
  <actions>
    <!-- 1️⃣ 선택된 ID 저장 -->
    <action type="update_data">
      <field>{selection_var_name}</field>

<value>
[
  {{선택된_ID}}
]
></value>

  
      <validated>true</validated>
    </action>
    
    <!-- 2️⃣ 완료 플래그 설정 -->
    <action type="update_data">
      <field>{flag_name}</field>
      <value>true</value>
      <validated>true</validated>
    </action>
    
    <!-- 3️⃣ 메인봇 호출 (복귀) -->
    <action type="complete_task">
      <summary>{bot_config.bot_id} 완료</summary>
    </action>
  </actions>
</bot_response>
```

⚠️ **액션 순서 설명:**
1. **update_data**: {selection_var_name}에 선택된 ID 저장
2. **update_data**: {flag_name}을 true로 설정
3. **call_subbot**: 메인봇 ID ({main_bot_id})로 호출
   - 현재 서브봇 종료
   - 메인봇으로 자동 복귀
   - 메인봇이 다음 빈 필드 처리 시작

🔥 **무효한 선택 시 즉시 응답:**
```xml
<bot_response>
  <message>{selection_validation.get('on_invalid', '선택하신 항목을 찾을 수 없습니다.')}

다시 선택해주세요:
{{목록_다시_제시}}</message>
  <actions></actions>
</bot_response>
```

⚠️ **중요:**
- 유효한 선택 → 3개 액션 (ID 저장 + flag true + call_subbot)
- 무효한 선택 → 다시 요청 (액션 없음)
- call_subbot으로 메인봇({main_bot_id})에 복귀합니다


⚠️ **CRITICAL - JSON 형식 규칙:**

**반드시 한 줄로 작성하세요!**
- 줄바꿈 금지 ❌
- 들여쓰기 금지 ❌
- 중괄호 이스케이프: `{{` `}}`

**올바른 예시:**
<value>[{{"coupon_id":"CUP001","title":"할인","discount_rate":25,"valid_until":"2025-08-31","min_amount":30000}}]</value>

**잘못된 예시 (줄바꿈):**
<value>
  [{{"coupon_id":"CUP001"}}]
</value>
"""
            
            return guide
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # C. 알 수 없는 타입
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    else:
        logger.error(f"❌ 알 수 없는 subbot_type: {subbot_type}")
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 오류: 알 수 없는 서브봇 타입
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

서브봇 타입: {subbot_type}
지원되는 타입: direct_return, selection_required
"""


def _format_parameters(param_list: list, current_data: dict) -> str:
    """API 파라미터를 포맷팅 (✅ 시스템 필드 제외)"""
    if not param_list:
        return "  (없음)"
    
    SYSTEM_FIELDS = {'message', 'room_id', 'user_id', 'timestamp'}
    
    result = []
    for param in param_list:
        if param in SYSTEM_FIELDS:
            continue
        value = current_data.get(param, 'N/A')
        result.append(f"  - {param}: {value}")
    
    return "\n".join(result) if result else "  (없음)"

def _format_parameters(param_list: list, current_data: dict) -> str:
    """API 파라미터를 포맷팅 (✅ 시스템 필드 제외)"""
    if not param_list:
        return "  (없음)"
    
    SYSTEM_FIELDS = {'message', 'room_id', 'user_id', 'timestamp'}
    
    result = []
    for param in param_list:
        if param in SYSTEM_FIELDS:
            continue
        value = current_data.get(param, 'N/A')
        result.append(f"  - {param}: {value}")
    
    return "\n".join(result) if result else "  (없음)"

def _format_parameters(param_list: list, current_data: dict) -> str:
    """API 파라미터를 포맷팅"""
    if not param_list:
        return "  (없음)"
    
    result = []
    for param in param_list:
        value = current_data.get(param, 'N/A')
        result.append(f"  - {param}: {value}")
    
    return "\n".join(result)

def _build_user_input_with_next_subbot_guide(
    current_var: dict,
    field_name: str,
    next_var: dict,
    next_field_name: str,
    current_step: dict,
    next_step: dict,
    bot_config: 'BotConfig',
    user_input: str = None  # ✅ 추가!
) -> str:
    """
    현재: user_input, 다음: 서브봇 호출
    """
    
    import logging
    logger = logging.getLogger(__name__)
    
    print("📝 _build_user_input_with_next_subbot_guide 시작")
    print(f"   현재 필드: {field_name}")
    print(f"   다음 서브봇: {next_field_name}")
    print(f"   사용자 입력: {user_input}")
    
    llm_guide = current_var.get('llm_execution_guide', {})
    
    # ✅ 질문 방법 (우선순위 적용)
    question = current_var.get('question', '')
    how_to_ask = llm_guide.get('how_to_ask', '')
    description = current_var.get('description', field_name)
    
    if question:
        prompt_text = question
    elif how_to_ask:
        prompt_text = how_to_ask
    else:
        prompt_text = f"{description}을(를) 입력해주세요."
    
    print(f"   질문 텍스트: {prompt_text[:50]}...")
    
    # ✅ 톤
    tone = llm_guide.get('user_friendly_tone', '친절하고 정중한')
    
    # ✅ 검증 규칙 (우선순위 적용)
    validation = llm_guide.get('validation', {})
    if not validation:
        validation = current_var.get('validation', {})
    
    rule = validation.get('rule', '문자열 입력')
    on_invalid = validation.get('on_invalid', '올바른 형식으로 다시 입력해주세요.')
    example_valid = validation.get('example_valid', [])
    example_invalid = validation.get('example_invalid', [])
    
    print(f"   검증 규칙: {rule[:50]}...")
    
    # ✅ 다음 서브봇 정보
    subbot_id = next_var.get('sub_bot_id', '')
    subbot_name = next_var.get('sub_bot_name', '')
    next_llm_guide = next_var.get('llm_execution_guide', {})
    before_execution = next_llm_guide.get('before_execution', '정보를 조회하고 있습니다...')
    
    print(f"   다음 서브봇 ID: {subbot_id}")
    print(f"   다음 서브봇 이름: {subbot_name}")
    
    after_collection = llm_guide.get('after_collection', '')
    
    guide = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 현재 필드 (사용자 입력)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<current_field>
  <field_name>{field_name}</field_name>
  <type>user_input</type>
  <question>{question}</question>
  <description>{description}</description>
  <data_type>{current_var.get('data_type', 'String')}</data_type>
  <is_mandatory>{current_var.get('is_mandatory', False)}</is_mandatory>
</current_field>

**질문 방법:**
{prompt_text}

**톤:** {tone}

**검증 규칙:**
- {rule}
- 유효 예시: {', '.join(example_valid) if example_valid else '없음'}
- 무효 예시: {', '.join(example_invalid) if example_invalid else '없음'}

**검증 실패 시:**
```xml<bot_response>
<message>{on_invalid}</message>
</bot_response>
"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ 사용자 입력이 있으면 명시!
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_input:
        guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 사용자 입력
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<user_input>
  <value>{user_input}</value>
  <target_field>{field_name}</target_field>
</user_input>

⚡ **중요: 사용자가 방금 "{user_input}"라고 입력했습니다.**

1. 이 값이 위의 검증 규칙을 만족하는지 확인하세요.
2. 만족하면 → {field_name}에 저장하고 서브봇 호출
3. 실패하면 → 검증 실패 메시지 출력 후 다시 질문
"""
    
    guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 다음 단계 (서브봇 호출)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<next_subbot>
  <subbot_id>{subbot_id}</subbot_id>
  <subbot_name>{subbot_name}</subbot_name>
  <field_name>{next_field_name}</field_name>
  <purpose>{next_var.get('purpose', '')}</purpose>
</next_subbot>

**수집 후 동작:**
{after_collection if after_collection else '서브봇 호출'}

**서브봇 실행 전 안내:**
{before_execution}

🔥 **현재 필드 검증 성공 시 즉시 응답:**
```xml<bot_response>
<message>감사합니다! {field_name}이(가) 확인되었습니다.{before_execution}</message>
<actions>
<action type="update_data">
<field>{field_name}</field>
<value>{{{user_input if user_input else '사용자_입력_값'}}}</value>
<validated>true</validated>
</action>
<action type="call_subbot">
<subbot_id>{subbot_id}</subbot_id>
<purpose>{next_var.get('purpose', '')}</purpose>
</action>
</actions>
</bot_response>

⚠️ **중요:**
- update_data로 현재 필드 저장
- call_subbot으로 서브봇 즉시 호출
- 서브봇 완료 후 결과가 {next_field_name}에 자동 저장됨
"""
    
    return guide




def _find_field_in_schema(field_name: str, data_schema: list) -> dict:
    """
    data_schema에서 필드 정보 찾기
    - field_name 또는 variable_name으로 검색
    - 서브봇 정보(sub_bot_id) 포함된 완전한 정보 반환
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not field_name:
        logger.warning("⚠️  _find_field_in_schema: field_name이 비어있음")
        return {}
    
    logger.debug(f"🔍 _find_field_in_schema 시작: {field_name}")
    logger.debug(f"   검색 대상: {len(data_schema)}개 필드")
    
    for i, field_info in enumerate(data_schema):
        # field_name 또는 variable_name으로 찾기
        info_field_name = field_info.get('field_name')
        info_variable_name = field_info.get('variable_name')
        
        if info_field_name == field_name or info_variable_name == field_name:
            logger.debug(f"   ✅ 발견! 인덱스 {i}")
            logger.debug(f"      field_name: {info_field_name}")
            logger.debug(f"      variable_name: {info_variable_name}")
            logger.debug(f"      field_type: {field_info.get('field_type', 'N/A')}")
            logger.debug(f"      sub_bot_id: {field_info.get('sub_bot_id', 'N/A')}")
            return field_info
    
    logger.warning(f"   ❌ 필드를 찾을 수 없음: {field_name}")
    logger.warning(f"   사용 가능한 필드들:")
    for i, field_info in enumerate(data_schema[:5]):  # 처음 5개만
        fn = field_info.get('field_name', 'N/A')
        vn = field_info.get('variable_name', 'N/A')
        logger.warning(f"      [{i}] field_name={fn}, variable_name={vn}")
    
    return {}


def _build_user_input_field_guide(
    current_var: dict,
    field_name: str,
    next_var: dict,
    next_field_name: str,
    current_step: dict,
    next_step: dict,
    bot_config: 'BotConfig',
    user_input: str = None  # ✅ 추가!
) -> str:
    """
    user_input 필드 가이드 생성
    - llm_execution_guide를 그대로 활용
    """
    
    import logging
    logger = logging.getLogger(__name__)
    
    print("📝 _build_user_input_field_guide 시작")
    print(f"   현재 필드: {field_name}")
    print(f"   사용자 입력: {user_input}")
    
    llm_guide = current_var.get('llm_execution_guide', {})
    
    # ✅ 질문 방법 (우선순위 적용)
    question = current_var.get('question', '')
    how_to_ask = llm_guide.get('how_to_ask', '')
    description = current_var.get('description', field_name)
    
    if question:
        prompt_text = question
    elif how_to_ask:
        prompt_text = how_to_ask
    else:
        prompt_text = f"{description}을(를) 입력해주세요."
    
    print(f"   질문 텍스트: {prompt_text[:50]}...")
    
    # ✅ 톤
    tone = llm_guide.get('user_friendly_tone', '친절하고 정중한')
    
    # ✅ 검증 규칙 (우선순위 적용)
    validation = llm_guide.get('validation', {})
    if not validation:
        # validation이 없으면 최상위에서 찾기
        validation = current_var.get('validation', {})
    
    rule = validation.get('rule', '문자열 입력')
    on_invalid = validation.get('on_invalid', '올바른 형식으로 다시 입력해주세요.')
    example_valid = validation.get('example_valid', [])
    example_invalid = validation.get('example_invalid', [])
    
    print(f"   검증 규칙: {rule[:50]}...")
    print(f"   유효 예시: {example_valid[:2]}")
    
    guide = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 현재 필드 (사용자 입력)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<current_field>
  <field_name>{field_name}</field_name>
  <type>user_input</type>
  <question>{question}</question>
  <description>{description}</description>
  <data_type>{current_var.get('data_type', 'String')}</data_type>
  <is_mandatory>{current_var.get('is_mandatory', False)}</is_mandatory>
</current_field>

**질문 방법:**
{prompt_text}

**톤:** {tone}

**검증 규칙:**
- {rule}
- 유효 예시: {', '.join(example_valid) if example_valid else '없음'}
- 무효 예시: {', '.join(example_invalid) if example_invalid else '없음'}

**검증 실패 시:**
```xml
<bot_response>
  <message>{on_invalid}</message>
</bot_response>
```
"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ 사용자 입력이 있으면 명시!
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_input:
        guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 사용자 입력
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<user_input>
  <value>{user_input}</value>
  <target_field>{field_name}</target_field>
</user_input>

⚡ **중요: 사용자가 방금 "{user_input}"라고 입력했습니다.**

1. 이 값이 위의 검증 규칙을 만족하는지 확인하세요.
2. 만족하면 → {field_name}에 저장하고 다음 필드로 진행
3. 실패하면 → 검증 실패 메시지 출력 후 다시 질문
"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 다음 필드 안내
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    after_collection = llm_guide.get('after_collection', '')
    
    if next_field_name and next_var:
        is_next_subbot = 'sub_bot_id' in next_var
        
        guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 다음 필드 (검증 성공 시)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<next_field>
  <field_name>{next_field_name}</field_name>
  <type>{'subbot_call' if is_next_subbot else 'user_input'}</type>
</next_field>
"""
        
        if not is_next_subbot:
            # 다음도 사용자 입력
            next_llm_guide = next_var.get('llm_execution_guide', {})
            
            # ✅ 우선순위 적용
            next_question = next_var.get('question', '')
            next_how_to_ask = next_llm_guide.get('how_to_ask', '')
            next_description = next_var.get('description', next_field_name)
            
            if next_question:
                next_prompt = next_question
            elif next_how_to_ask:
                next_prompt = next_how_to_ask
            else:
                next_prompt = f"{next_description}을(를) 입력해주세요."
            
            print(f"   다음 질문: {next_prompt[:50]}...")
            
            guide += f"""
**수집 후 동작:**
{after_collection if after_collection else '다음 필드로 진행'}

**다음 질문:**
{next_prompt}

🔥 **현재 필드 검증 성공 시 즉시 응답:**
```xml
<bot_response>
  <message>감사합니다! {field_name}이(가) 확인되었습니다.

{next_prompt}</message>
  <actions>
    <action type="update_data">
      <field>{field_name}</field>
      <value>{{{user_input if user_input else '사용자_입력_값'}}}</value>
      <validated>true</validated>
    </action>
  </actions>
</bot_response>
```
"""
        
        else:
            # 다음은 서브봇
            subbot_id = next_var.get('sub_bot_id', '')
            subbot_name = next_var.get('sub_bot_name', '')
            next_llm_guide = next_var.get('llm_execution_guide', {})
            before_execution = next_llm_guide.get('before_execution', '정보를 조회하고 있습니다...')
            
            guide += f"""
**수집 후 동작:**
{after_collection if after_collection else '서브봇 호출'}

**다음 단계:** 서브봇 호출 ({subbot_name})

🔥 **현재 필드 검증 성공 시 즉시 응답:**
```xml
<bot_response>
  <message>감사합니다! {field_name}이(가) 확인되었습니다.

{before_execution}</message>
  <actions>
    <action type="update_data">
      <field>{field_name}</field>
      <value>{{{user_input if user_input else '사용자_입력_값'}}}</value>
      <validated>true</validated>
    </action>
    <action type="call_subbot">
      <subbot_id>{subbot_id}</subbot_id>
      <purpose>{next_var.get('purpose', '')}</purpose>
    </action>
  </actions>
</bot_response>
```
"""
    
    else:
        # 현재 step의 마지막 필드
        if next_step:
            guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 현재 단계 완료 → 다음 단계로
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**수집 후 동작:**
{after_collection if after_collection else '다음 단계로 진행'}

다음 단계: {next_step.get('action', '')}

🔥 **현재 필드 검증 성공 시:**
```xml
<bot_response>
  <message>감사합니다! {current_step.get('action', '')} 단계가 완료되었습니다.

이제 {next_step.get('action', '')} 단계를 진행하겠습니다.</message>
  <actions>
    <action type="update_data">
      <field>{field_name}</field>
      <value>{{{user_input if user_input else '사용자_입력_값'}}}</value>
      <validated>true</validated>
    </action>
  </actions>
</bot_response>
```
"""
        else:
            # 최종 완료
            guide += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 모든 단계 완료!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**수집 후 동작:**
{after_collection if after_collection else '작업 완료'}

🔥 **현재 필드 검증 성공 시:**
```xml
<bot_response>
  <message>감사합니다! 모든 정보가 확인되었습니다.
{bot_config.task_name}을(를) 완료합니다.</message>
  <actions>
    <action type="update_data">
      <field>{field_name}</field>
      <value>{{{user_input if user_input else '사용자_입력_값'}}}</value>
      <validated>true</validated>
    </action>
    <action type="complete_task">
      <summary>{bot_config.task_name} 완료</summary>
    </action>
  </actions>
</bot_response>
```
"""
    
    return guide


def _build_final_completion_prompt(bot_config: 'BotConfig', current_data: Dict[str, Any]) -> str:
    """최종 완료 프롬프트"""
    import logging
    logger = logging.getLogger(__name__)
    
    print("🎉 _build_final_completion_prompt 호출")
    print(f"   봇: {bot_config.task_name}")
    
    filled_fields = []
    for field_name, value in current_data.items():
        if not field_name.endswith('_completed') and value:
            filled_fields.append({'name': field_name, 'value': value})
    
    print(f"   수집된 필드: {len(filled_fields)}개")
    
    filled_xml = "<collected_data>\n"
    for f in filled_fields:
        filled_xml += f"  ✅ {f['name']}: {f['value']}\n"
    filled_xml += "</collected_data>"
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 최종 목표
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{bot_config.final_goal}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 수집된 모든 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{filled_xml}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 모든 단계 완료!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 **즉시 작업 완료:**
```xml
<bot_response>
  <message>모든 정보가 확인되었습니다! {bot_config.task_name}을(를) 완료합니다.</message>
  <actions>
    <action type="complete_task">
      <summary>{bot_config.task_name} 완료</summary>
    </action>
  </actions>
</bot_response>
```
"""

def dict_to_xml(data: Dict[str, Any], root_tag: str = "data") -> str:
    """
    ✅ 개선: 채워진 필드와 빈 필드를 시각적으로 구분
    """
    lines = [f"<{root_tag}>"]
    
    filled_count = 0
    empty_count = 0
    
    for key, value in data.items():
        # API 자동 주입 필드 제외
        if key in ['message', 'room_id', 'member_id']:
            continue
            
        if value is None or (isinstance(value, str) and not value.strip()):
            lines.append(f"  <{key} status=\"EMPTY\">null</{key}>  <!-- 🔴 수집 필요 -->")
            empty_count += 1
        else:
            lines.append(f"  <{key} status=\"FILLED\">{value}</{key}>  <!-- ✅ 완료 - 다시 묻지 마세요 -->")
            filled_count += 1
    
    lines.append(f"  <!-- 📊 통계: 완료 {filled_count}개 / 필요 {empty_count}개 -->")
    lines.append(f"</{root_tag}>")
    return "\n".join(lines)


def schema_to_xml(schema: List[Dict[str, Any]]) -> str:
    """데이터 스키마를 XML로 변환"""
    lines = ["<schema>"]
    for field in schema:
        field_name = field.get('field_name', '')
        description = field.get('description', '')
        prompt_guide = field.get('prompt_guide', '')
        validation = field.get('validation_rule', {})
        
        lines.append(f"  <field name=\"{field_name}\">")
        lines.append(f"    <description>{description}</description>")
        if prompt_guide:
            lines.append(f"    <guide>{prompt_guide}</guide>")
        if validation:
            lines.append(f"    <validation>{validation}</validation>")
        lines.append(f"  </field>")
    lines.append("</schema>")
    return "\n".join(lines)


def clean_client_reply(reply):
    """기존 응답 정리 함수 - 완전 보존"""
    reply = re.sub(r'Conversation History.*?(?=\n\n|\[DATA_COLLECTED|\[System Notification|$)', '', reply, flags=re.DOTALL | re.IGNORECASE).strip()
    reply = re.sub(r'\[System Notification.*?\]|🔴 \[긴급 수행 지시\].*?\*\*지금 바로 행동하십시오\.\*\*|--- TASK CONFIG.*?---|\[CRITICAL INSTRUCTION.*?\]', '', reply, flags=re.DOTALL | re.IGNORECASE).strip()
    reply = re.sub(r'(User:|Model:)', '', reply).strip() 
    reply = re.sub(r'\[DATA_COLLECTED:.*?\]', '', reply, flags=re.DOTALL | re.IGNORECASE).strip()
    reply = re.sub(r'\n\s*\n', '\n', reply).strip()
    return reply

def execute_webhook(task_config: Dict, collected_data: Dict) -> str:
    """기존 웹훅 함수 - 완전 보존"""
    print(f" 🚀 웹훅 실행! 데이터: {collected_data}")
    return "모든 정보가 확인되어 쿠폰이 발급되었습니다! (Webhook Success)"

# ============================================
# STEP 1: Configuration 계층화
# ============================================

@dataclass
class BotConfig:
    """봇 설정을 담는 데이터 클래스"""
    
    # 필수 필드를 Optional로 만들거나 기본값 제공
    bot_id: str = ""  # ← 기본값 추가
    
    bot_name: str = ""
    task_name: str = ""
    job_title: str = ""
    service_type: str = ""
    final_goal: str = ""
    prompt_template: str = ""
    
    service_workflow: Dict = field(default_factory=dict)
    all_variables: List = field(default_factory=list)
    data_schema: List = field(default_factory=list)
    completion_condition: Dict = field(default_factory=dict)
    subbot_mapping: Dict = field(default_factory=dict)
    callable_sub_bots: List = field(default_factory=list)
    call_triggers: Dict = field(default_factory=dict)
    response_rules: Dict = field(default_factory=dict)
    webhook_spec: Dict = field(default_factory=dict)
    summary: Dict = field(default_factory=dict)
    activation_conditions: Dict = field(default_factory=dict)
    
    is_subbot: bool = False
    subbot_type: str = ""
    api_endpoint: str = ""
    trigger_keywords: List = field(default_factory=list)
    execution_logic: Dict = field(default_factory=dict)
    selection_config: Optional[Dict] = None
    llm_execution_guide: Dict = field(default_factory=dict)
    
    # ✅ 핵심: 알 수 없는 필드 처리
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BotConfig':
        """
        딕셔너리에서 BotConfig 생성 (안전 버전)
        - 알려진 필드: 직접 할당
        - 알 수 없는 필드: extra_fields에 저장
        """
        import dataclasses
        
        known_fields = {f.name for f in dataclasses.fields(cls)} - {'extra_fields'}
        
        # 알려진 필드만 추출
        known_data = {k: v for k, v in data.items() if k in known_fields}
        
        # 알 수 없는 필드는 extra_fields에 저장
        unknown_data = {k: v for k, v in data.items() if k not in known_fields}
        
        return cls(**known_data, extra_fields=unknown_data)
    
    def get(self, key: str, default=None):
        """필드 또는 extra_fields에서 값 가져오기"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra_fields.get(key, default)
    
    def to_dict(self) -> dict:
        """BotConfig를 딕셔너리로 변환"""
        from dataclasses import asdict
        result = asdict(self)
        
        # extra_fields 병합
        extra = result.pop('extra_fields', {})
        result.update(extra)
        
        return result
    

@dataclass
class RoomConfig:
    """방 설정 (1:N 구조)"""
    room_id: str
    main_bot_id: str
    sub_bots: List[str]

class ConfigManager:
    """설정 관리자 - DB 기반"""
    
    def __init__(self):
        self.rooms: Dict[str, RoomConfig] = {}
        self.bots: Dict[str, BotConfig] = {}
        self.prompt_templates: Dict[str, Any] = {}
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🆕 DB 기반 로드
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def load_from_database(self, db: BotDatabase):
        """
        DB에서 봇 목록 조회 → 파일에서 정의 로드
        """
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📂 DB에서 봇 설정 로드 중...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 1. DB에서 활성화된 봇 목록 조회
        all_bots = db.get_all_bots(active_only=True)
        
        print(f"\n활성 봇: {len(all_bots)}개\n")
        
        # 2. 각 봇의 정의 파일 로드
        for bot_meta in all_bots:
            bot_id = bot_meta['bot_id']
            bot_type = bot_meta['bot_type']
            
            try:
                # 파일에서 JSON 로드
                bot_definition = db.get_bot_definition(bot_id)
                if not bot_definition:
                    print(f"  ❌ {bot_id}: 정의 파일 로드 실패")
                    continue
                
                # 프롬프트 로드
                prompt_content = db.get_bot_prompt(bot_id)
                if not prompt_content:
                    print(f"  ⚠️  {bot_id}: 프롬프트 없음")
                    prompt_content = ""
                is_subbot = (bot_type == 'service') 
                # BotConfig 생성 (기존 스키마 → 새 스키마 변환)
                bot_config = self._convert_to_bot_config(
                    bot_id,
                    bot_definition,
                    prompt_content,
                    is_subbot=is_subbot
                  
                )

                # bot_config = BotConfig(
                #         bot_id=bot_definition['bot_id'],
                #         bot_name=bot_definition['task_name'],
                #         prompt_template=prompt_content,
                #         data_schema=bot_definition['data_schema'],
                #         completion_condition=bot_definition['completion_condition'],

                #         callable_sub_bots=bot_definition.get('callable_sub_bots', []),
                #         call_triggers=bot_definition.get('call_triggers', {}),

                #         activation_conditions=bot_definition.get('activation_conditions', {}),
                       
                #         is_subbot=is_subbot  # 🔥 전달!
                #     )
    


                self.bots[bot_id] = bot_config
                
                print(f"  ✅ {bot_id} ({bot_meta['bot_type']})")
                print(f"     이름: {bot_config.bot_name}")
                print(f"     프롬프트: {len(prompt_content)} chars")
                
            except Exception as e:
                print(f"  ❌ {bot_id} 로드 실패: {e}")
        
        # 3. 방 설정 로드
        # 3. 방 설정 로드
        print("\n[방 설정 로드]")
        all_rooms = db.get_all_rooms()

        print(f"DB에서 조회된 방: {len(all_rooms)}개\n")

        for room_meta in all_rooms:
            room_id = str(room_meta['room_id'])
            main_bot_id = str(room_meta['main_bot_id'])
            
            print(f"  🔍 Room {room_id}: main_bot='{main_bot_id}'")
            
            # 🆕 메인 봇 검증 (경고만 출력, 스킵하지 않음)
            if main_bot_id not in self.bots:
                print(f"     ⚠️  메인 봇 '{main_bot_id}' 로드되지 않음")
                print(f"     💡 방은 생성하지만 봇 기능 제한됨")
                sub_bots = []  # 서브봇도 없음
            else:
                # 서브 봇 찾기 (메인 봇의 callable_sub_bots)
                main_bot = self.bots[main_bot_id]
                sub_bots = main_bot.callable_sub_bots
            
            # 🆕 RoomConfig 생성 (메인 봇 없어도 생성)

            print(f"  🔑 Before Save. Keys: {list(self.rooms.keys())}")
            self.rooms[room_id] = RoomConfig(
                room_id=room_id,
                main_bot_id=main_bot_id,
                sub_bots=sub_bots
            )

            print(f"  🔑 After Save. Keys: {list(self.rooms.keys())}")
            
            print(f"  ✅ {room_id} → {main_bot_id}")
            if sub_bots:
                print(f"     서브봇: {', '.join(sub_bots)}")

        print(f"\n✅ 로드 완료: Rooms {len(self.rooms)}개, Bots {len(self.bots)}개")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔧 기존 스키마 → BotConfig 변환
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _convert_to_bot_config(
        self, 
        bot_id: str, 
        bot_definition: dict, 
        prompt_content: str,
        is_subbot: bool
    ) -> BotConfig:
        """
        JSON 정의 → BotConfig 객체 변환
        
        기존 스키마(task_config1.json)와 
        새 스키마 둘 다 지원
        """
        
        import logging
        logger = logging.getLogger(__name__)
        
        print("=" * 80)
        print("🔄 _convert_to_bot_config 시작")
        print("=" * 80)
        print(f"📌 bot_id: {bot_id}")
        print(f"📌 is_subbot: {is_subbot}")
        print(f"📌 bot_definition 키: {list(bot_definition.keys())}")
        
        # # 🔥 스키마 판별
        # if 'data_requirements' in bot_definition:
        #     # 새 스키마
        #     return self._parse_new_schema(bot_id, bot_definition, prompt_content,is_subbot)
        # else:
        #     # 기존 스키마 (task_config1.json 형식)
        return self._parse_legacy_schema(bot_id, bot_definition, prompt_content, is_subbot)
    
    def _parse_legacy_schema(self, bot_id: str, data: dict, prompt: str, is_subbot: bool) -> BotConfig:
        """
        기존 스키마 파싱 (task_config1.json)
        
        핵심 원칙: 통째로 복사!
        """
        
        import logging
        logger = logging.getLogger(__name__)
        
        print("-" * 80)
        print("📋 _parse_legacy_schema 시작")
        print("-" * 80)
        print(f"🔍 bot_id: {bot_id}")
        print(f"🔍 is_subbot: {is_subbot}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. 기본 정보
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        task_name = data.get('task_name', bot_id)
        job_title = data.get('job_title', '')
        service_type = data.get('service_type', '')
        
        print(f"📌 task_name: {task_name}")
        print(f"📌 job_title: {job_title}")
        print(f"📌 service_type: {service_type}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. data_schema 통째로 가져오기
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        data_schema = data.get('data_schema', [])
        print(f"📊 data_schema: {len(data_schema)}개 필드")
        
        for i, field in enumerate(data_schema):
            field_name = field.get('field_name', 'N/A')
            field_type = field.get('field_type', 'N/A')
            print(f"   [{i}] {field_name} (type: {field_type})")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3. service_workflow
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        service_workflow = data.get('service_workflow', {})
        print(f"📋 service_workflow: {len(service_workflow)}개 step")
        
        for step_key, step_info in sorted(service_workflow.items()):
            print(f"   {step_key}: {step_info.get('action', 'N/A')}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4. all_variables
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        all_variables = data.get('all_variables', [])
        print(f"📊 all_variables: {len(all_variables)}개 변수")
        
        for var in all_variables:
            var_name = var.get('variable_name', 'N/A')
            is_sub = 'sub_bot_id' in var
            print(f"   - {var_name} ({'서브봇' if is_sub else '사용자입력'})")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5. subbot_mapping에서 서브봇 정보 추출
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        subbot_mapping = data.get('subbot_mapping', {})
        print(f"🤖 subbot_mapping: {len(subbot_mapping)}개 서브봇")
        
        for subbot_id, subbot_info in subbot_mapping.items():
            print(f"   - {subbot_id}: {subbot_info.get('sub_bot_name', 'N/A')}")
        
        # callable_sub_bots: 호출 가능한 서브봇 ID 리스트
        callable_sub_bots = list(subbot_mapping.keys())
        print(f"📞 callable_sub_bots: {callable_sub_bots}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 6. call_triggers (키워드 → 서브봇 ID 매핑)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        call_triggers = data.get('call_triggers', {})
        print(f"🔔 call_triggers: {len(call_triggers)}개 트리거")
        
        for keyword, subbot_id in call_triggers.items():
            print(f"   '{keyword}' → {subbot_id}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 7. completion_condition
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        completion_condition = data.get('completion_condition', {})
        must_fill = completion_condition.get('must_fill', [])
        print(f"✅ completion_condition.must_fill: {must_fill}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 8. activation_conditions
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        activation = data.get('activation_conditions', {})
        print(f"🎯 activation_conditions: {activation}")
        
        # mission_required인 경우 추가
        if activation.get('mission_required'):
            mission_bot_id = activation.get('mission_config_id')
            print(f"   📢 mission_required! mission_bot_id: {mission_bot_id}")
            
            if mission_bot_id and mission_bot_id not in callable_sub_bots:
                callable_sub_bots.append(mission_bot_id)
                print(f"      → callable_sub_bots에 추가됨")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 9. 서브봇 전용 필드 (is_subbot=True일 때)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        subbot_type = ""
        api_endpoint = ""
        trigger_keywords = []
        execution_logic = {}
        selection_config = None
        llm_execution_guide = {}
        
        if is_subbot:
            print("🔧 서브봇 전용 필드 추출")
            
            subbot_type = data.get('subbot_type', 'direct_return')
            api_endpoint = data.get('api_endpoint', '')
            trigger_keywords = data.get('trigger_keywords', [])
            execution_logic = data.get('execution_logic', {})
            selection_config = data.get('selection_config')
            llm_execution_guide = data.get('llm_execution_guide', {})
            
            print(f"   subbot_type: {subbot_type}")
            print(f"   api_endpoint: {api_endpoint}")
            print(f"   trigger_keywords: {trigger_keywords}")
            print(f"   selection_config: {'있음' if selection_config else '없음'}")
            print(f"   llm_execution_guide: {'있음' if llm_execution_guide else '없음'}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 10. 기타 메타데이터
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        final_goal = data.get('final_goal', '')
        response_rules = data.get('response_rules', {})
        webhook_spec = data.get('webhook_spec', {})
        summary = data.get('summary', {})
        
        print(f"📝 final_goal: {final_goal[:50] if final_goal else '없음'}...")
        print(f"📋 response_rules: {'있음' if response_rules else '없음'}")
        print(f"🌐 webhook_spec: {'있음' if webhook_spec else '없음'}")
        print(f"📊 summary: {summary}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 11. BotConfig 생성 (from_dict 사용으로 안전하게)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("🏗️  BotConfig 객체 생성")
        print("-" * 80)
        
        # 모든 필드를 딕셔너리로 준비
        config_data = {
            'bot_id': bot_id,
            'bot_name': task_name,
            'task_name': task_name,
            'job_title': job_title,
            
            # 프롬프트
            'prompt_template': prompt,
            
            # 메인 데이터
            'service_type': service_type,
            'service_workflow': service_workflow,
            'all_variables': all_variables,
            'final_goal': final_goal,
            
            # data_schema
            'data_schema': data_schema,
            
            # 완료 조건
            'completion_condition': completion_condition,
            
            # 서브봇 관련
            'subbot_mapping': subbot_mapping,
            'callable_sub_bots': callable_sub_bots,
            'call_triggers': call_triggers,
            
            # 활성화 조건
            'activation_conditions': activation,
            
            # 서브봇 여부 및 전용 필드
            'is_subbot': is_subbot,
            'subbot_type': subbot_type,
            'api_endpoint': api_endpoint,
            'trigger_keywords': trigger_keywords,
            'execution_logic': execution_logic,
            'selection_config': selection_config,
            'llm_execution_guide': llm_execution_guide,
            
            # 추가 메타데이터
            'response_rules': response_rules,
            'webhook_spec': webhook_spec,
            'summary': summary
        }
        
        # ✅ from_dict로 안전하게 생성 (알 수 없는 필드도 처리)
        bot_config = BotConfig.from_dict(config_data)
        
        print("✅ BotConfig 생성 완료")
        print(f"   bot_id: {bot_config.bot_id}")
        print(f"   task_name: {bot_config.task_name}")
        print(f"   is_subbot: {bot_config.is_subbot}")
        print(f"   data_schema: {len(bot_config.data_schema)}개")
        print(f"   callable_sub_bots: {len(bot_config.callable_sub_bots)}개")
        
        # extra_fields가 있으면 로그 출력
        if bot_config.extra_fields:
            print(f"   📦 extra_fields: {list(bot_config.extra_fields.keys())}")
        
        print("=" * 80)
        
        return bot_config
        

    
    # def _parse_new_schema(self, bot_id: str, data: dict, prompt: str ,is_subbot: bool) -> BotConfig:
    #     """새 스키마 파싱"""
        
    #     # data_requirements.fields → data_schema 변환
    #     data_schema = []
    #     for field in data.get('data_requirements', {}).get('fields', []):
    #         data_schema.append({
    #             'field_name': field.get('field_name'),
    #             'description': field.get('description', ''),
    #             'prompt_guide': field.get('acquisition_config', {}).get('prompt_guide', ''),
    #             'is_mandatory': field.get('required', False),
    #             'validation_rule': field.get('acquisition_config', {}).get('validation', {}),
    #             'default_value': field.get('acquisition_config', {}).get('value')
    #         })
        
    #     # callable_sub_bots 추출
    #     callable_sub_bots = []
    #     for field in data.get('data_requirements', {}).get('fields', []):
    #         if field.get('acquisition_method') == 'service_bot':
    #             service_bot_id = field.get('acquisition_config', {}).get('service_bot_id')
    #             if service_bot_id and service_bot_id not in callable_sub_bots:
    #                 callable_sub_bots.append(service_bot_id)
        
    #     return BotConfig(
    #         bot_id=bot_id,
    #         bot_name=data.get('bot_name', bot_id),
    #         prompt_template=prompt,
    #         data_schema=data_schema,
    #         completion_condition=data.get('completion', {}).get('conditions', {}),
    #         callable_sub_bots=callable_sub_bots,
    #         call_triggers={},  # 새 스키마에서는 acquisition_config에 포함
    #         activation_conditions={},
    #         is_subbot=is_subbot
    #     )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 기존 메서드들 (그대로 유지)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def get_room_config(self, room_id) -> Optional[RoomConfig]:
        """Room Config 조회 (타입 정규화)"""
        
        # 🔍 디버깅: 입력값 확인
        print(f"\n🔍 [get_room_config] 호출됨")
        print(f"   입력 room_id: {room_id!r} (타입: {type(room_id).__name__})")
        
        # 🔍 디버깅: 현재 저장된 키 확인
        print(f"   저장된 키들: {list(self.rooms.keys())}")
        print(f"   키 타입들: {[type(k).__name__ for k in self.rooms.keys()]}")
        
        # 타입 정규화
        normalized_id = str(room_id)
        print(f"   정규화 후: {normalized_id!r}")
        
        # 조회
        result = self.rooms.get(normalized_id)
        print(f"   조회 결과: {result}")
        
        return result
    
    def get_bot_config(self, bot_id: str) -> Optional[BotConfig]:
        return self.bots.get(bot_id)
# ============================================
# STEP 2: State Manager (스택 기반 상태 관리)
# ============================================

class BotState(Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"

@dataclass
class BotStackFrame:
    bot_id: str
    state: BotState
    entry_time: str
    local_history: List[Dict[str, str]] = field(default_factory=list)



class SessionStateManager:
    """세션 상태 관리 - 기존 TASK_SESSIONS 대체"""
    
    def __init__(self, session_id: str, main_bot_id: str, user_id: str = None, room_id: str = None):
        self.session_id = session_id
        self.main_bot_id = main_bot_id
        self.user_id = user_id or session_id  # ← 추가
        self.room_id = room_id or session_id  # ← 추가
        self.bot_stack: List[BotStackFrame] = [
            BotStackFrame(
                bot_id=main_bot_id,
                state=BotState.ACTIVE,
                entry_time=datetime.utcnow().isoformat()
            )
        ]
        self.shared_context: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, str]] = []
        self.llm_call_count = 0
        self.task_completed = False
        self.metadata: Dict[str, Any] = {}  # ✅ 메타데이터 추가 (서브봇 실행 이력 등)
    def update_main_bot(self, new_main_bot_id: str):
        """
        메인 봇 업데이트 (봇 재설계 시 사용)
        
        ⚠️ 주의: 진행 중인 작업이 리셋됩니다
        """
        if len(self.bot_stack) == 1:
            # 메인 봇만 있을 때 (서브봇 없음)
            old_bot_id = self.bot_stack[0].bot_id
            self.bot_stack[0] = BotStackFrame(
                bot_id=new_main_bot_id,
                state=BotState.ACTIVE,
                entry_time=datetime.utcnow().isoformat()
            )
            print(f"🔄 [Session] 메인봇 업데이트: {old_bot_id} → {new_main_bot_id}")
            return True
        else:
            print(f"⚠️ [Session] 서브봇 실행 중이라 메인봇 업데이트 불가 (스택 깊이: {len(self.bot_stack)})")
            return False
    
    def reset_to_main_bot(self, new_main_bot_id: str):
        """
        강제로 메인 봇으로 리셋 (모든 서브봇 제거)
        """
        old_bot_id = self.bot_stack[0].bot_id
        self.bot_stack = [
            BotStackFrame(
                bot_id=new_main_bot_id,
                state=BotState.ACTIVE,
                entry_time=datetime.utcnow().isoformat()
            )
        ]
        # 기존 컨텍스트는 유지하거나 리셋할지 선택
        # self.shared_context = {}  # 리셋하려면 주석 해제
        print(f"🔄 [Session] 강제 리셋: {old_bot_id} → {new_main_bot_id} (스택 깊이: {len(self.bot_stack)})")
    def increment_llm_calls(self):
        self.llm_call_count += 1
        print(f"📊 [LLM Call Counter] 현재 호출 횟수: {self.llm_call_count}")
    def get_active_bot(self) -> str:
        for frame in reversed(self.bot_stack):
            if frame.state == BotState.ACTIVE:
                return frame.bot_id
        return self.bot_stack[0].bot_id
    
    def push_bot(self, bot_id: str):
        """새 봇 호출"""
        for frame in self.bot_stack:
            if frame.state == BotState.ACTIVE:
                frame.state = BotState.WAITING
        
        self.bot_stack.append(
            BotStackFrame(
                bot_id=bot_id,
                state=BotState.ACTIVE,
                entry_time=datetime.utcnow().isoformat()
            )
        )
        print(f"📥 [State] 봇 스택 추가: {bot_id} (깊이: {len(self.bot_stack)})")
    
    def pop_bot(self) -> Optional[str]:
        """봇 종료 후 복귀"""
        if len(self.bot_stack) <= 1:
            print("⚠️ [State] 메인 봇은 pop 불가")
            return None

        completed_frame = self.bot_stack.pop()
        completed_frame.state = BotState.COMPLETED
        self.bot_stack[-1].state = BotState.ACTIVE

        restored_bot_id = self.bot_stack[-1].bot_id
        print(f"📤 [State] 봇 복귀: {completed_frame.bot_id} → {restored_bot_id}")
        return restored_bot_id

    def get_metadata(self, key: str, default=None):
        """메타데이터 조회"""
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value):
        """메타데이터 설정"""
        self.metadata[key] = value

# ============================================
# STEP 3: Router (규칙 기반 라우팅)
# ============================================

class BotRouter:
    """봇 전환 로직"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def should_transfer(self, user_message: str, current_bot_id: str) -> Optional[str]:
        """키워드 기반 봇 전환 판단"""
        bot_config = self.config_manager.get_bot_config(current_bot_id)
        if not bot_config:
            return None
        
        for keyword, target_bot_id in bot_config.call_triggers.items():
            if keyword in user_message:
                print(f"🎯 [Router] 트리거 감지: '{keyword}' → {target_bot_id}")
                return target_bot_id
        
        return None
    
    def check_completion(self, bot_id: str, collected_data: Dict[str, Any]) -> bool:
        """완료 조건 체크 (기존 check_completion 로직)"""
        bot_config = self.config_manager.get_bot_config(bot_id)
        if not bot_config:
            return False
        
        must_fill = bot_config.completion_condition.get('must_fill', [])
        
        for field in must_fill:
            if field not in collected_data or not collected_data[field]:
                print(f" ⏳ 미완료: '{field}' 누락")
                return False
        
        print(f"✅ [Router] 봇 '{bot_id}' 완료 조건 충족")
        return True

# ============================================
# STEP 4: 통합 세션 관리자
# ============================================

class SessionManager:
    """전체 세션 관리 - 기존 로직 통합"""
    
    def __init__(self, config_manager: ConfigManager):
        self.sessions: Dict[str, SessionStateManager] = {}
        self.user_session_map: Dict[str, str] = {}
        self.config_manager = config_manager
        self.router = BotRouter(config_manager)
        
        # ✅ XML 파서와 실행기 초기화
        self.xml_parser = XMLToolParser()
        self.xml_executor = XMLActionExecutor(config_manager)
    
    def clear_room_sessions(self, room_id: str) -> int:
        """
        특정 방의 모든 세션 초기화
        
        Args:
            room_id: 방 ID
            
        Returns:
            초기화된 세션 개수
        """
        room_id = str(room_id)
        cleared_count = 0
        
        # room_id로 시작하는 모든 user_key 찾기
        keys_to_remove = []
        for user_key in list(self.user_session_map.keys()):
            if user_key.startswith(f"{room_id}:"):
                session_id = self.user_session_map[user_key]
                
                # 세션 삭제
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    cleared_count += 1
                    print(f"   🗑️  세션 삭제: {session_id} (user: {user_key})")
                
                keys_to_remove.append(user_key)
        
        # user_session_map에서 제거
        for key in keys_to_remove:
            del self.user_session_map[key]
        
        return cleared_count
    def get_or_create_session(self, room_id: str, member_id: str) -> Tuple[SessionStateManager, bool]:
        """세션 복구 또는 생성 (XML 기반)"""
        user_key = f"{room_id}:{member_id}"
        is_new = False
        
        # 기존 세션 확인
        if user_key in self.user_session_map:
            session_id = self.user_session_map[user_key]
            if session_id in self.sessions:
                return self.sessions[session_id], is_new
        
        # 새 세션 생성
        room_config = self.config_manager.get_room_config(room_id)
        if not room_config:
            raise ValueError(f"Room {room_id} not found")
        

        
        session_id = str(uuid.uuid4())
        session = SessionStateManager(session_id, room_config.main_bot_id, user_id=member_id,  room_id=room_id    )
        print(f"👤 [User] {member_id}")
        print(f"🏠 [Room] {room_id}")
        
        # Bot Config 가져오기
        bot_config = self.config_manager.get_bot_config(room_config.main_bot_id)
        if not bot_config:
            raise ValueError(f"Bot {room_config.main_bot_id} not found")
        
        # 초기 데이터 설정 (coupon_user_id = member_id)
        initial_field = None
        for field in bot_config.data_schema:
            if field.get('field_name') == 'coupon_user_id':
                initial_field = 'coupon_user_id'
                break
        
        if initial_field:
            session.shared_context[initial_field] = member_id
        
        # 🆕 기본값 즉시 적용
        self.apply_default_values(session, room_config.main_bot_id)
        
       
        # 세션 저장
        self.sessions[session_id] = session
        self.user_session_map[user_key] = session_id
        is_new = True
        
        # 로깅
        initial_data_json = json.dumps(session.shared_context, ensure_ascii=False, indent=2)
        print(f"✨ [Session] 신규 세션 생성: {session_id} (Main: {room_config.main_bot_id})")
        print(f"📊 [Initial Data] {initial_data_json}")
    
        
        return session, is_new


    
    def apply_default_values(self, session: SessionStateManager, bot_id: str):
        """all_variables의 example을 기본값으로 주입"""
        bot_config = self.config_manager.get_bot_config(bot_id)
        if not bot_config:
            return
        
        all_variables = bot_config.all_variables
        if not all_variables:
            return
        
        for var_info in all_variables:
            var_name = var_info.get('variable_name')
            example_val = var_info.get('example')
            
            if var_name and example_val is not None and example_val != "null":
                if var_name not in session.shared_context:
                    session.shared_context[var_name] = example_val
                    print(f"   ✅ 기본값 주입: {var_name} = {example_val}")
    
    def build_xml_system_prompt(self,
        bot_config: 'BotConfig',
        session:SessionStateManager,
        current_data: Dict[str, Any],
        task_completed: bool = False ,
        config_manager: 'ConfigManager' = None
    ) -> str:
        """
        service_workflow 기반 동적 시스템 프롬프트 생성
        """
        
        import logging
        logger = logging.getLogger(__name__)

        logger.setLevel(logging.INFO)
        
        print("=" * 80)
        print("🚀 build_xml_system_prompt 시작")
        print("=" * 80)
        print(f"📌 bot_config.bot_id: {bot_config.bot_id}")
        print(f"📌 bot_config.task_name: {bot_config.task_name}")
        print(f"📌 bot_config.is_subbot: {bot_config.is_subbot}")
        print(f"📌 task_completed: {task_completed}")
        print(f"📌 current_data 키 목록: {list(current_data.keys())}")
        print(f"📌 current_data 내용: {current_data}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 0️⃣ 작업 완료 체크
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if task_completed:
            print("✅ task_completed=True → 완료 프롬프트 반환")
            return f"""
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ✅ 작업 완료됨
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    <bot_response>
    <message>작업이 이미 완료되었습니다. 감사합니다!</message>
    </bot_response>
    """
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 0️⃣-2 서브봇 체크
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if bot_config.is_subbot:
            print("🔧 is_subbot=True → _build_subbot_prompt 호출")
            print(f"   서브봇 ID: {bot_config.bot_id}")
            print(f"   서브봇 이름: {bot_config.task_name}")
            return _build_subbot_prompt(bot_config, current_data)
        
        print("🏢 메인봇 프롬프트 생성 시작")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1️⃣ service_workflow 파싱
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("1️⃣ service_workflow 파싱")
        print("-" * 80)
        
        service_workflow = bot_config.service_workflow


        # all_variables = bot_config.all_variables

        data_schema = bot_config.data_schema
        
        print(f"📋 전체 workflow step 개수: {len(service_workflow)}")
        print(f"📋 전체 변수 개수: {len(data_schema)}")
        
        sorted_steps = sorted(service_workflow.items(), key=lambda x: x[0])
        
        for step_key, step_info in sorted_steps:
            print(f"   {step_key}: {step_info.get('action', '')} (required: {step_info.get('required_info', [])})")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2️⃣ 현재 step 찾기
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("2️⃣ 현재 step 찾기")
        print("-" * 80)
        
        current_step_key = None
        current_step_info = None
        next_step_key = None
        next_step_info = None
        
        for i, (step_key, step_info) in enumerate(sorted_steps):
            required_info = step_info.get('required_info', [])
            
            print(f"🔍 {step_key} 검사 중...")
            print(f"   required_info: {required_info}")
            
            all_filled = True
            for var_name in required_info:
                value = current_data.get(var_name)
                has_value = value is not None and (not isinstance(value, str) or value.strip())
                print(f"      - {var_name}: {value} (채워짐={has_value})")
                
                if not has_value:
                    all_filled = False
            
            print(f"   → all_filled: {all_filled}")
            
            if not all_filled:
                current_step_key = step_key
                current_step_info = step_info
                print(f"✅ 현재 step 발견: {step_key}")
                
                if i + 1 < len(sorted_steps):
                    next_step_key = sorted_steps[i + 1][0]
                    next_step_info = sorted_steps[i + 1][1]
                    print(f"   다음 step: {next_step_key}")
                else:
                    print(f"   다음 step: 없음 (마지막 step)")
                break
        
        if not current_step_info:
            print("✅ 모든 step 완료 → _build_final_completion_prompt 호출")
            return _build_final_completion_prompt(bot_config, current_data)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3️⃣ 이미 채운 필드 정리 (✅ 수정)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("3️⃣ 이미 채운 필드 정리")
        print("-" * 80)
        
        # ✅ 시스템 필드 정의
        SYSTEM_FIELDS = {'message', 'room_id', 'user_id', 'timestamp'}
        
        filled_fields = []
        user_input_message = None
        
        for field_name, value in current_data.items():
            # 시스템 필드 처리
            if field_name in SYSTEM_FIELDS:
                if field_name == 'message':
                    user_input_message = value  # ✅ 사용자 입력 저장
                    print(f"   💬 사용자 입력 메시지: {value}")
                else:
                    print(f"   ⏭️  {field_name}: 스킵 (시스템 필드)")
                continue
            
            if field_name.endswith('_completed'):
                print(f"   ⏭️  {field_name}: 스킵 (완료 플래그)")
                continue
            
            if value is not None and str(value).strip():
                filled_fields.append({'name': field_name, 'value': value})
                print(f"   ✅ {field_name}: {value}")
        
        print(f"📊 총 {len(filled_fields)}개 비즈니스 필드 완료됨")
        print(f"💬 사용자 메시지: {user_input_message}")
        
        # ✅ filled_xml에는 비즈니스 필드만!
        filled_xml = "<already_filled>\n"
        if filled_fields:
            filled_xml += "  ⚠️ 아래 필드들은 이미 완료. 절대 다시 묻지 마세요!\n\n"
            for f in filled_fields:
                filled_xml += f"  ✅ {f['name']}: {f['value']}\n"
        else:
            filled_xml += "  (아직 수집된 정보 없음)\n"
        filled_xml += "</already_filled>"
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4️⃣ 현재 step의 required_info에서 처리할 필드 찾기
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("4️⃣ 현재 step의 처리할 필드 찾기")
        print("-" * 80)
        
        # current_required = current_step_info.get('required_info', [])
        # print(f"📋 현재 step({current_step_key})의 required_info: {current_required}")
        
        current_field_name = None
        next_field_name = None
        
        all_fields_in_order = []
        for step_key, step_info in sorted_steps:
            required_info = step_info.get('required_info', [])
            for field_name in required_info:
                all_fields_in_order.append({
                    'step_key': step_key,
                    'field_name': field_name,
                    'step_info': step_info
                })

        print(f"📋 전체 필드 순서: {len(all_fields_in_order)}개")
        for i, field_item in enumerate(all_fields_in_order):
            value = current_data.get(field_item['field_name'])
            is_filled = value is not None and (not isinstance(value, str) or value.strip())
            status = "✅ 완료" if is_filled else "⏳ 대기"
            print(f"   [{i}] {field_item['step_key']}.{field_item['field_name']} ({status})")

        # ✅ 현재 필드와 다음 필드 찾기
        current_field_name = None
        current_field_step = None
        current_field_index = None
        next_field_name = None
        next_field_step = None

        for i, field_item in enumerate(all_fields_in_order):
            field_name = field_item['field_name']
            value = current_data.get(field_name)
            is_empty = value is None or (isinstance(value, str) and not value.strip())
            
            print(f"🔍 [{i}] {field_item['step_key']}.{field_name}: value={value}, is_empty={is_empty}")
            
            if is_empty:
                if current_field_name is None:
                    # ✅ 현재 필드 발견
                    current_field_name = field_name
                    current_field_step = field_item['step_key']
                    current_field_index = i
                    print(f"   ✅ 현재 필드로 설정: {current_field_step}.{field_name}")
                    
                    # ✅ 다음 필드 찾기 (이미 채워진 필드는 건너뛰기!)
                    for j in range(i + 1, len(all_fields_in_order)):
                        next_field_item = all_fields_in_order[j]
                        next_field_candidate = next_field_item['field_name']
                        next_value = current_data.get(next_field_candidate)
                        next_is_empty = next_value is None or (isinstance(next_value, str) and not next_value.strip())
                        
                        print(f"   🔍 다음 필드 후보 [{j}] {next_field_item['step_key']}.{next_field_candidate}: is_empty={next_is_empty}")
                        
                        if next_is_empty:
                            # ✅ 비어있는 다음 필드 발견!
                            next_field_name = next_field_candidate
                            next_field_step = next_field_item['step_key']
                            print(f"   ✅ 다음 필드로 설정: {next_field_step}.{next_field_name}")
                            break
                        else:
                            print(f"   ⏭️  스킵 (이미 채워짐)")
                    
                    if not next_field_name:
                        print(f"   ℹ️  다음 빈 필드 없음 (모두 완료 또는 마지막)")
                    
                    break  # ✅ 현재 필드 찾았으면 종료

        print(f"📌 현재 처리할 필드: {current_field_step}.{current_field_name if current_field_name else 'None'}")
        print(f"📌 다음 빈 필드: {next_field_step}.{next_field_name if next_field_name else 'None'}")

        # ✅ current_step_info는 현재 필드가 속한 step으로 업데이트
        if current_field_step:
            for step_key, step_info in sorted_steps:
                if step_key == current_field_step:
                    current_step_info = step_info
                    current_step_key = step_key
                    break

        # ✅ next_step_info는 다음 필드가 속한 step으로 설정
        next_step_info = None
        if next_field_step:
            for step_key, step_info in sorted_steps:
                if step_key == next_field_step:
                    next_step_info = step_info
                    break

            
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5️⃣ classification에서 변수 정보 찾기 (✅ 수정)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("5️⃣ classification에서 변수 정보 찾기")
        print("-" * 80)
        
        current_var = _find_field_in_schema(current_field_name, data_schema)
        next_var = _find_field_in_schema(next_field_name, data_schema) if next_field_name else None
        
        if current_var:
            print(f"✅ 현재 변수 찾음: {current_field_name}")
            print(f"   variable_id: {current_var.get('variable_id', 'N/A')}")
            print(f"   question: {current_var.get('question', 'N/A')[:50] if current_var.get('question') else 'N/A'}...")
            print(f"   description: {current_var.get('description', 'N/A')[:50] if current_var.get('description') else 'N/A'}...")
            print(f"   sub_bot_id: {current_var.get('sub_bot_id', '없음 (user_input)')}")
            
            # ✅ llm_execution_guide 구조 확인
            llm_guide = current_var.get('llm_execution_guide', {})
            print(f"   llm_execution_guide: {'있음' if llm_guide else '없음'}")
            if llm_guide:
                print(f"      키 목록: {list(llm_guide.keys())}")
                print(f"      how_to_ask: {'있음' if llm_guide.get('how_to_ask') else '없음'}")
                print(f"      validation: {'있음' if llm_guide.get('validation') else '없음'}")
        else:
            logger.error(f"❌ 현재 변수를 찾을 수 없음: {current_field_name}")
            return f"ERROR: {current_field_name} 변수를 찾을 수 없습니다."
        
        if next_var:
            print(f"✅ 다음 변수 찾음: {next_field_name}")
            print(f"   variable_id: {next_var.get('variable_id', 'N/A')}")
            print(f"   question: {next_var.get('question', 'N/A')[:50] if next_var.get('question') else 'N/A'}...")
            print(f"   sub_bot_id: {next_var.get('sub_bot_id', '없음 (user_input)')}")
            
            # ✅ 다음 변수의 llm_execution_guide 확인
            next_llm_guide = next_var.get('llm_execution_guide', {})
            print(f"   llm_execution_guide: {'있음' if next_llm_guide else '없음'}")
            if next_llm_guide:
                print(f"      how_to_ask: {'있음' if next_llm_guide.get('how_to_ask') else '없음'}")
        else:
            print(f"ℹ️  다음 변수 없음 (현재 step의 마지막 필드)")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 6️⃣ 현재 필드가 서브봇이면 에러!
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("6️⃣ 현재 필드 타입 검증")
        print("-" * 80)
        
        is_current_subbot = 'sub_bot_id' in current_var
        print(f"🔍 현재 필드 타입: {'서브봇 ❌' if is_current_subbot else 'user_input ✅'}")

        if is_current_subbot:
            sub_bot_id = current_var.get('sub_bot_id', '')

            # ✅✅✅ 서브봇 실행 이력 확인 (중복 호출 방지!)
            executed_subbots = session.get_metadata('executed_subbots', {})

            if sub_bot_id in executed_subbots:
                print(f"⏭️  서브봇 이미 실행됨: {sub_bot_id}")
                print(f"   실행 시각: {executed_subbots[sub_bot_id].get('timestamp', 'N/A')}")
                print(f"   호출자: {executed_subbots[sub_bot_id].get('called_from', 'N/A')}")
                print(f"   ➡️  다음 필드로 건너뛰기")

                # 다음 필드로 이동
                if next_field_name and next_var:
                    print(f"   📌 다음 필드를 현재 필드로 재설정: {next_field_name}")
                    current_field_name = next_field_name
                    current_var = next_var

                    # 다음 필드도 서브봇인지 재확인
                    is_current_subbot = 'sub_bot_id' in current_var

                    if is_current_subbot:
                        # 다음 필드도 서브봇! 재귀적으로 체크 필요
                        logger.warning(f"⚠️  연속된 서브봇 필드 감지: {next_field_name}")
                        # 간단하게는 다음 서브봇도 실행 이력 확인 후 처리
                        # 복잡한 경우 재귀 호출 고려
                        # 여기서는 일단 경고만 출력하고 계속 진행
                        # (다음 턴에서 다시 처리됨)
                else:
                    # 다음 필드 없음 → 모든 필드 완료
                    print(f"   ✅ 모든 필드 완료!")
                    return _build_final_completion_prompt(bot_config, current_data)

            else:
                # 서브봇이 아직 실행되지 않았음 → 즉시 서브봇으로 전환!
                print(f"🤖 서브봇으로 전환!")
                print(f"   필드명: {current_field_name}")
                print(f"   서브봇 ID: {sub_bot_id}")

                sub_bot_config = config_manager.get_bot_config(sub_bot_id)

                if not sub_bot_config:
                    logger.error(f"❌ 서브봇 설정을 찾을 수 없음: {sub_bot_id}")
                    return f"ERROR: 서브봇 설정을 찾을 수 없습니다: {sub_bot_id}"

                print(f"✅ 서브봇 설정 로드 완료: {sub_bot_config.task_name}")

                # ✅ 1. 서브봇 실행 이력 기록
                from datetime import datetime
                executed_subbots[sub_bot_id] = {
                    'called_from': bot_config.bot_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                session.set_metadata('executed_subbots', executed_subbots)
                print(f"   📝 서브봇 실행 이력 기록")

                # ✅ 2. 서브봇으로 전환 (push_bot)
                session.push_bot(sub_bot_id)
                print(f"   🔄 봇 스택 전환: {bot_config.bot_id} → {sub_bot_id}")

                # ✅ 3. 히스토리 백업 (서브봇은 깨끗한 상태로 시작)
                session._main_bot_history = list(session.conversation_history)
                session.conversation_history = []
                print(f"   🧹 히스토리 백업 완료")

                # ✅ 4. 서브봇 프롬프트 생성 (경로 1: bot_config.is_subbot과 동일)
                print(f"   📄 서브봇 프롬프트 생성 (_build_subbot_prompt 호출)")
                return _build_subbot_prompt(sub_bot_config, current_data) 
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 7️⃣ 현재 step 안내
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("7️⃣ 프롬프트 헤더 생성")
        print("-" * 80)
        
        step_header = f"""
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🎯 최종 목표
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {bot_config.final_goal}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    📊 현재 상태
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {filled_xml}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🎯 현재 단계: {current_step_key}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    <current_step>
    <action>{current_step_info.get('action', '')}</action>
    <purpose>{current_step_info.get('purpose', '')}</purpose>
    <stage>{current_step_info.get('stage', '')}</stage>

    </current_step>
    """
        
        print(f"✅ 헤더 생성 완료")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 8️⃣ 다음 필드가 서브봇인 경우 구분 (✅ 수정)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("8️⃣ 필드 가이드 생성 분기")
        print("-" * 80)
        
        is_next_subbot = next_var and 'sub_bot_id' in next_var
        
        print(f"🔍 다음 필드 타입: {('서브봇 🔧' if is_next_subbot else 'user_input 👤') if next_var else '없음 ⏹️'}")
        
        if is_next_subbot:
            print("📞 _build_user_input_with_next_subbot_guide 호출")
            print(f"   현재 필드: {current_field_name} (user_input)")
            print(f"   다음 서브봇: {next_field_name} (sub_bot_id: {next_var.get('sub_bot_id', '')})")
            
            field_guide = _build_user_input_with_next_subbot_guide(
                current_var,
                current_field_name,
                next_var,
                next_field_name,
                current_step_info,
                next_step_info,
                bot_config,
                user_input_message  # ✅ 추가!
            )
        else:
            print("👤 _build_user_input_field_guide 호출")
            print(f"   현재 필드: {current_field_name} (user_input)")
            print(f"   다음 필드: {next_field_name if next_field_name else '없음'}")
            
            field_guide = _build_user_input_field_guide(
                current_var,
                current_field_name,
                next_var,
                next_field_name,
                current_step_info,
                next_step_info,
                bot_config,
                user_input_message  # ✅ 추가!
            )
        
        print("✅ 필드 가이드 생성 완료")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 9️⃣ 절대 규칙
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("-" * 80)
        print("9️⃣ 절대 규칙 추가")
        print("-" * 80)
        
        response_rules = bot_config.response_rules
        absolute_rules = response_rules.get('절대_규칙', {})
        rules_text = "\n".join([f"{v}" for v in absolute_rules.values()])
        
        print(f"📋 절대 규칙 개수: {len(absolute_rules)}")
        
        print("=" * 80)
        print("✅ build_xml_system_prompt 완료")
        print("=" * 80)
        
        return f"""{step_header}

    {field_guide}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🚨 절대 규칙
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {rules_text}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    📊 실행 흐름
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    1. 현재 필드에 대한 사용자 입력 검증
    2. 검증 성공 → update_data + 다음 질문 출력
    3. 시스템이 데이터 저장만 처리
    4. 사용자가 다음 필드에 대해 응답
    5. 현재 step 완료 → 다음 step으로 자동 진행
    6. 모든 step 완료 → complete_task
    """

    def build_llm_messages(self, session, bot_id, user_message):
        """XML 기반 메시지 생성"""
        bot_config = self.config_manager.get_bot_config(bot_id)
        if not bot_config:
            return []
        # 🆕 추가: 어느 봇의 프롬프트를 사용하는지 명시
        print(f"\n{'━'*60}")
        print(f"🤖 [Build Messages] 봇: {bot_id} ({bot_config.bot_name})")
        # print(f"   프롬프트 길이: {bot_config.prompt_template} chars")


        # # 🆕 프롬프트 내용 미리보기
        # if bot_config.prompt_template:
        #     preview = bot_config.prompt_template.replace('\n', ' ')
        #     print(f"   프롬프트 미리보기: {preview}...")
        # else:
        #     print(f"   ❌ 경고: 프롬프트가 비어있음!")



        print(f"{'━'*60}")
        # ✅ XML 기반 시스템 프롬프트 생성
        system_prompt = self.build_xml_system_prompt(bot_config, session,session.shared_context, task_completed=session.task_completed ,config_manager=self.config_manager)
        print(f"   📝 최종 시스템 프롬프트: {system_prompt} ")




      
        messages = [{"role": "system", "content": system_prompt}]
        
        # if bot_config.is_subbot:
        #     print(f"   🤖 [Subbot Mode] 히스토리 제외")
        # else:
        #     # 히스토리 추가 (메인봇만)
        #     if user_message:
        #         messages.extend(session.conversation_history)
        #         messages.append({"role": "user", "content": user_message})
        #     else:
        #         messages.extend(session.conversation_history)
        
        print(f"📚 [Messages] {len(messages)}개")
        print(f"📊 [Current Data] {json.dumps(session.shared_context, ensure_ascii=False)}")
        
        return messages  # ✅ tools 반환 제거
        
        
    def _print_current_state(self, session, user_message):
        """현재 상태 출력"""
        current_bot_id = session.get_active_bot()
        
        print(f"\n{'='*60}")
        print(f"📥 [User Input] {user_message}")
        print(f"🤖 [Active Bot] {current_bot_id}")
        print(f"📚 [Bot Stack] {' → '.join(f.bot_id for f in session.bot_stack)}")
        print(f"📊 [Current Data]")
        print(f"👤 [User] {session.user_id}")  # ← 추가
        print(f"🏠 [Room] {session.room_id}")  # ← 추가
        
        for key, value in session.shared_context.items():
            if key not in ['message', 'room_id', 'member_id']:
                status = "✅" if value else "❌"
                display = str(value)[:50] if value else "None"
                print(f"   {status} {key}: {display}")
        
        print(f"{'='*60}\n")


    def _call_llm_and_execute(self, session, user_message):
        """
        LLM 호출 및 액션 실행
        
        ✅ 봇 전환도 여기서 완료됨!
        """
        current_bot_id = session.get_active_bot()
        
        # LLM 메시지 구성
        messages = self.build_llm_messages(session, current_bot_id, user_message)

        
        
        print(f"🔄 [LLM Call] 메시지: {len(messages)}개")
        
        # LLM 호출
        llm_response_text = send_llm_request_xml(messages)
        
        print(f"🤖 [LLM Response]{current_bot_id}{llm_response_text}...")
        
        # XML 파싱
        natural_message, actions = self.xml_parser.parse(llm_response_text)
        
        print(f"💬 [Natural] {natural_message[:100] if natural_message else '(없음)'}...")
        print(f"🔧 [Actions] {len(actions)}개")
        
        # 히스토리 추가
        session.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        session.conversation_history.append({
            "role": "assistant",
            "content": natural_message or "(작업 수행됨)"
        })
        
        # ✅ 액션 실행 (봇 전환 포함!)
        action_result = self.xml_executor.execute_actions(
            actions, 
            session, 
            self.config_manager
        )
        
        return {
            'natural_message': natural_message,
            'completed': action_result.get('completed', False),
            'bot_changed': action_result.get('bot_changed', False),
            'target_bot_id': action_result.get('target_bot_id'),
            'data_updated': action_result.get('data_updated', False)
        }


    def _generate_new_bot_initial_message(self, session, new_bot_id, transition_message):
        """
        새 봇으로 전환 후 초기 메시지 생성
        
        ✅ transition_message를 먼저 반환하고
        ✅ 백그라운드에서 서브봇 LLM 호출
        """
        print(f"\n{'='*60}")
        print(f"🤖 [New Bot Initial] {new_bot_id}")
        print(f"   Transition Message: {transition_message[:50] if transition_message else 'None'}...")
        print(f"{'='*60}\n")
        
        # 1. transition_message를 히스토리에 추가
        if transition_message and transition_message.strip():
            session.conversation_history.append({
                "role": "assistant",
                "content": transition_message
            })
        
        #✅ 2. 백그라운드 스레드로 서브봇 LLM 호출
        def background_subbot_init():
            try:
                print(f"   🧵 [Background] 서브봇 LLM 호출 시작")
                
                # 새 봇 초기 메시지 생성
                messages = self.build_llm_messages(session, new_bot_id, "")

                
                print(f"   🔄 [Background] LLM 호출")
                
                response_text = send_llm_request_xml(messages)
                natural, actions = self.xml_parser.parse(response_text)
                
                print(f"   ✅ [Background] 서브봇 LLM 완료:{new_bot_id} {response_text}...")
                
                # 히스토리에 추가
                session.conversation_history.append({
                    "role": "assistant",
                    "content": natural
                })
                
                # 추가 액션 실행
                if actions:
                    print(f"   🔧 [Background] {len(actions)}개 액션 실행")
                    self.xml_executor.execute_actions(actions, session, self.config_manager)
                
                # ✅ WebSocket으로 클라이언트에게 전송!
              
              
                
                # ✅ 봇 정보 가져오기
                bot_config = self.config_manager.get_bot_config(new_bot_id)
                bot_name = bot_config.bot_name if bot_config else new_bot_id
                bot_type = "메인봇" if len(session.bot_stack) == 1 else "서브봇"
                
                # WebSocket 전송
                send_to_user(
                    room_id=session.room_id,
                    user_id=session.user_id,
                    event='bot_message',
                    data={
                        'message': natural,
                        'bot_id': new_bot_id,
                        'bot_name': bot_name,  # ✅ 추가
                        'bot_type': bot_type,  # ✅ 추가
                        'type': 'text'
                    }
                )
                
                print(f"   📤 bot_message → {session.user_id} ({bot_type}: {bot_name})")
                
            except Exception as e:
                print(f"   ❌ [Background] 에러: {e}")
                import traceback
                traceback.print_exc()
                
                # 에러도 WebSocket으로 전송
                try:
                  
                    send_to_user(
                        room_id=session.room_id,
                        user_id=session.user_id,
                        event='error',
                        data={
                            'error': str(e),
                            'message': '서브봇 처리 중 오류가 발생했습니다.',
                            'bot_id': new_bot_id,
                            'bot_name': "",  # ✅ 추가
                            'bot_type': "",  # ✅ 추가
                        }
                    )
                except:
                    pass
        
        # 3. 스레드 시작
        import threading
        thread = threading.Thread(target=background_subbot_init, daemon=True)
        thread.start()
        print(f"   🚀 [Background] 스레드 시작됨")
        
        # 4. 즉시 transition_message 반환
        return {
            "reply": clean_client_reply(transition_message) if transition_message else "처리 중입니다...",
            "bot_changed": True,
            "new_bot_id": new_bot_id,
            "background_processing": True
        }

    def _handle_subbot_completion(self, session, subbot_message):
        """서브봇 완료 → 메인봇 복귀"""
        
        completed_bot_id = session.get_active_bot()
        main_bot_id = session.pop_bot()
        
        print(f"\n{'='*60}")
        print(f"🔄 [Subbot Return] {completed_bot_id} → {main_bot_id}")
        print(f"{'='*60}\n")
        
        # 완료 플래그 자동 저장
        bot_config = self.config_manager.get_bot_config(main_bot_id)
        if hasattr(bot_config, 'subbot_mapping'):
            for meta in bot_config.subbot_mapping.values():
                subbot_id_in_meta = meta.get('sub_bot_id') or meta.get('subbot_id')
                if subbot_id_in_meta == completed_bot_id:
                    flag = f"{meta['variable_name']}_completed"
                    session.shared_context[flag] = True
                    print(f"   ✅ {flag} = True")
        
        # 히스토리 복원
        if hasattr(session, '_main_bot_history'):
            session.conversation_history = session._main_bot_history
            delattr(session, '_main_bot_history')
        
        # 서브봇 완료 플래그 리셋
        session.task_completed = False
        
        # 🔥 메인봇 프롬프트 생성 (build_llm_messages만 사용!)
        messages = self.build_llm_messages(session, main_bot_id, "")
        
        # LLM 호출
        response_text = send_llm_request_xml(messages)
        
        print(f"   🚀 [메인봇 복귀] LLM 응답 수신")
        
        # 파싱 및 실행
        relay_natural, relay_actions = self.xml_parser.parse(response_text)
        
        relay_result = self.xml_executor.execute_actions(
            relay_actions, 
            session, 
            self.config_manager
        )
        
        # 히스토리 추가
        session.conversation_history.append({
            "role": "assistant",
            "content": relay_natural
        })
        
        # # 완료 체크
        # if relay_result.get('completed'):
        #     return self._handle_main_bot_completion(session, relay_natural, subbot_message)
        
        # 응답 반환
        return {
            "reply": clean_client_reply(relay_natural),
            "bot_changed": True,
            "returned_from_subbot": True
        }

    def _handle_main_bot_completion(self, session, main_message, subbot_message=None):
        """메인봇 완료 → 웹훅"""
        
        print(f"\n{'='*60}")
        print(f"✅ [Main Bot Complete]")
        print(f"{'='*60}\n")
        
        current_bot_id = session.get_active_bot()
        bot_config = self.config_manager.get_bot_config(current_bot_id)
        
        webhook_result = execute_webhook(
            {'id': bot_config.bot_id, 'name': bot_config.bot_name},
            session.shared_context
        )
        
        # 메시지 조합
        if subbot_message:
            combined = f"{subbot_message}\n\n{webhook_result}"
        else:
            combined = f"{clean_client_reply(main_message)}\n\n{webhook_result}"
        
        return {
            "reply": combined,
            "completed": True
        }
    def handle_message(self, session: SessionStateManager, user_message: str) -> Dict[str, Any]:
        """
        메시지 처리 (최종 단순화)
        
        흐름:
        1. 전처리
        2. LLM 호출 및 액션 실행 (봇 전환 포함)
        3. 상태별 후처리
        4. 응답 반환
        """
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 0️⃣ 전처리
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        current_bot_id = session.get_active_bot()
        
        # 완료 체크 (메인봇만)
        if session.task_completed and current_bot_id == session.main_bot_id:
            return {
                "reply": "작업이 이미 완료되었습니다. 감사합니다!",
                "completed": True
            }
        
        # 입력 검증
        # if not user_message or not user_message.strip():
        #     return {"reply": "메시지를 입력해주세요.", "error": "empty_message"}
        
        # # ✅ 서브봇 초기화 직후 중복 메시지 무시
        # if getattr(session, 'subbot_just_started', False):
        #     print("⏭️ 서브봇 초기화 중 - 사용자 입력 무시")
        #     print(f"   무시된 메시지: {user_message}")
        #     session.subbot_just_started = False
        #     return {
        #         "reply": "",  # 빈 응답
        #         "skip": True,  # 무시 플래그
        #         "bot_changed": False
        #     }
        
        # 상태 출력
        self._print_current_state(session, user_message)
        
        # 기본값 적용
        # self.apply_default_values(session, current_bot_id)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1️⃣ LLM 호출 및 액션 실행
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        llm_result = self._call_llm_and_execute(session, user_message)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2️⃣ 상태별 후처리
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ 2-0. 누락 필드 요청 처리
        if llm_result.get('ask_for_missing'):
            return {
                "reply": llm_result['missing_field_message'],
                "completed": False,
                "missing_fields": llm_result.get('missing_fields', [])
            }
        
        # 2-1. 봇 전환됨 → 새 봇 초기 메시지 생성
        if llm_result['bot_changed']:
            # ✅ 서브봇으로 전환 시 플래그 설정
            # session.subbot_just_started = True
            print("🚀 서브봇 초기화 플래그 설정")
            
            return self._generate_new_bot_initial_message(
                session, 
                llm_result['target_bot_id'],
                llm_result['natural_message']
            )
        
        # 2-2. 서브봇 완료 → 메인봇 복귀
        if llm_result['completed']:


            return self._handle_subbot_completion(
                session, 
                llm_result['natural_message']
            )
        
        # # 2-3. 메인봇 완료 → 웹훅
        # if llm_result['completed'] and current_bot_id == session.main_bot_id:
        #     return self._handle_main_bot_completion(
        #         session, 
        #         llm_result['natural_message']
        #     )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3️⃣ 일반 응답
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        return {
            "reply": clean_client_reply(llm_result['natural_message']),
            "bot_changed": False,
            "data_updated": llm_result['data_updated']
        }


# ============================================
# Flask API 엔드포인트
# ============================================
def create_bot_list_response(bots):
    """봇 목록 위젯 응답 생성"""
    return {
        "type": "bot_management",
        "widget_type": "bot_list",
        "content": f"등록된 봇 {len(bots)}개",
        "bots": [
            {
                "bot_id": bot['bot_id'],
                "bot_name": bot['bot_name'],
                "bot_type": bot['bot_type'],
                "is_active": bot['is_active'] == 1,
                "field_count": bot['field_count'],
                "has_webhook": bot['has_webhook'] == 1,
                "goal_description": bot['goal_description'],
                "created_at": bot['created_at']
            }
            for bot in bots
        ]
    }


def create_bot_detail_response(bot):
    """봇 상세 위젯 응답 생성"""
    return {
        "type": "bot_management",
        "widget_type": "bot_detail",
        "content": f"'{bot['bot_name']}' 상세 정보",
        "bot": {
            "bot_id": bot['bot_id'],
            "bot_name": bot['bot_name'],
            "bot_type": bot['bot_type'],
            "is_active": bot['is_active'] == 1,
            "version": bot['version'],
            "field_count": bot['field_count'],
            "has_webhook": bot['has_webhook'] == 1,
            "goal_description": bot['goal_description'],
            "created_at": bot['created_at'],
            "updated_at": bot['updated_at']
        }
    }


def create_bot_form_response(mode='create', bot_data=None):
    """봇 생성/수정 폼 위젯 응답 생성"""
    return {
        "type": "bot_management",
        "widget_type": "bot_create_form" if mode == 'create' else "bot_edit_form",
        "content": "새 봇을 만듭니다" if mode == 'create' else f"'{bot_data['bot_name']}' 수정",
        "bot": bot_data if mode == 'edit' else None
    }


def create_confirm_dialog_response(action, target_name, target_id):
    """확인 다이얼로그 위젯 응답 생성"""
    messages = {
        "삭제": f"'{target_name}' 봇을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.",
        "비활성화": f"'{target_name}' 봇을 비활성화하시겠습니까?"
    }
    
    return {
        "type": "bot_management",
        "widget_type": "confirm_dialog",
        "title": f"⚠️ {action} 확인",
        "message": messages.get(action, f"{action}하시겠습니까?"),
        "confirm_action": f"확인:{action}:{target_id}",
        "confirm_text": "확인",
        "cancel_text": "취소"
    }


def create_room_list_response(rooms):
    """방 목록 위젯 응답 생성"""
    return {
        "type": "bot_management",
        "widget_type": "room_list",
        "content": f"등록된 방 {len(rooms)}개",
        "rooms": [
            {
                "room_id": room['room_id'],
                "room_name": room['room_name'],
                "main_bot_id": room['main_bot_id'],
                "created_at": room['created_at']
            }
            for room in rooms
        ]
    }


def create_room_assign_form_response(room, available_bots):
    """방 봇 할당 폼 위젯 응답 생성"""
    return {
        "type": "bot_management",
        "widget_type": "room_assign_form",
        "content": f"'{room['room_name']}'에 봇 할당",
        "room": room,
        "available_bots": [
            {
                "bot_id": bot['bot_id'],
                "bot_name": bot['bot_name'],
                "bot_type": bot['bot_type']
            }
            for bot in available_bots
        ]
    }


def create_text_response(content):
    """일반 텍스트 응답 생성"""
    return {
        "type": "text",
        "content": content
    }



def save_bot_design_files(llm_response: str, category_id: str, output_dir: str = "./bot_designs"):
    """
    LLM 응답에서 XML 태그(<file>)를 기준으로 파일을 추출하여 저장.
    """
    
    print("="*80)
    print("🔍 [DEBUG] save_bot_design_files 시작")
    print(f"   category_id: {category_id}")
    print(f"   응답 길이: {len(llm_response)} 글자")
    print("="*80)


    step3_json = None
    
    # 1. 저장 디렉토리 생성
    bot_dir = Path(output_dir) / category_id
    bot_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 디렉토리 생성: {bot_dir}")
    
    saved_files = {}

    # 2. XML 기반 정규표현식 패턴
    pattern = r"<file>\s*<filename>(.*?)</filename>\s*<content>(.*?)</content>\s*</file>"
    
    print("\n🔍 [DEBUG] XML 패턴으로 매칭 시도...")
    print(f"   패턴: {pattern}")
    
    matches = list(re.finditer(pattern, llm_response, re.DOTALL))
    
    print(f"   매칭 결과: {len(matches)}개 발견")
    
    if not matches:
        print("\n❌ [ERROR] <file> 태그를 찾을 수 없습니다!")
        print("\n📝 응답 미리보기 (처음 500자):")
        print("-"*80)
        print(llm_response[:500])
        print("-"*80)
        
        print("\n🔍 '<file>' 키워드 검색:")
        if "<file>" in llm_response:
            print("   ✅ '<file>' 발견됨")
            idx = llm_response.find("<file>")
            print(f"   위치: {idx}")
            print(f"   주변 텍스트: {llm_response[max(0, idx-50):idx+150]}")
        else:
            print("   ❌ '<file>' 없음")
        
        print("\n🔍 '<filename>' 키워드 검색:")
        if "<filename>" in llm_response:
            print("   ✅ '<filename>' 발견됨")
            idx = llm_response.find("<filename>")
            print(f"   위치: {idx}")
            print(f"   주변 텍스트: {llm_response[max(0, idx-50):idx+150]}")
        else:
            print("   ❌ '<filename>' 없음")
        
        # 전체 응답 백업
        backup_path = bot_dir / "full_response_backup.txt"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(llm_response)
        print(f"\n💾 전체 응답 백업: {backup_path}")
        
        return {
            "error": {
                "path": str(backup_path),
                "status": "not_found",
                "error": "응답에서 <file> 태그를 찾을 수 없습니다."
            }
        }

    print(f"\n✅ {len(matches)}개 파일 발견! 처리 시작...\n")

    for i, match in enumerate(matches, 1):
        filename = match.group(1).strip()
        raw_content = match.group(2).strip()
        
        print(f"📄 [{i}/{len(matches)}] 파일 처리 중: {filename}")
        print(f"   원본 내용 길이: {len(raw_content)} 글자")
        
        # 3. 마크다운 코드 블록 제거
        clean_content = raw_content
        
        if clean_content.startswith("```json"):
            print("   🧹 ```json 제거 중...")
            clean_content = clean_content[7:]
        elif clean_content.startswith("```"):
            print("   🧹 ``` 제거 중...")
            first_newline = clean_content.find('\n')
            if first_newline != -1:
                clean_content = clean_content[first_newline+1:]
        
        if clean_content.strip().endswith("```"):
            print("   🧹 마지막 ``` 제거 중...")
            clean_content = clean_content.strip()[:-3]
        
        clean_content = clean_content.strip()
        print(f"   정제 후 길이: {len(clean_content)} 글자")

        # 4. JSON 파일 전용 정제
        if filename.endswith('.json'):
            print("   🔧 JSON 파일 전용 정제 시작...")
            
            start_index = clean_content.find('{')
            print(f"      첫 번째 '{{' 위치: {start_index}")
            
            if start_index != -1:
                json_candidate = clean_content[start_index:]
                end_index = json_candidate.rfind('}')
                print(f"      마지막 '}}' 위치: {end_index}")
                
                if end_index != -1:
                    clean_content = json_candidate[:end_index + 1]
                    print(f"      JSON 추출 완료: {len(clean_content)} 글자")

        file_path = bot_dir / filename

        # 5. 파일 저장
        file_info = {
            "path": str(file_path),
            "size": 0,
            "status": "pending"
        }

        try:
            if filename.endswith('.json'):
                print("   📝 JSON 파싱 시도...")
                try:
                    json_data = json.loads(clean_content)
                    print(f"      ✅ JSON 파싱 성공!")

                    if filename == "intermediate_step3.json":
                        step3_json = json_data
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    file_info["status"] = "success"
                    print(f"      💾 파일 저장 완료: {file_path}")
                    
                except json.JSONDecodeError as e:
                    print(f"      ❌ JSON 파싱 실패: {str(e)}")
                    print(f"      에러 위치: line {e.lineno}, column {e.colno}")
                    
                    # 원본 저장
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(clean_content)
                    file_info["status"] = "warning"
                    file_info["error"] = f"JSON 파싱 실패 (원본 저장됨): {str(e)}"
                    print(f"      💾 원본 그대로 저장: {file_path}")
            
            else:
                print("   📝 텍스트 파일로 저장...")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(clean_content)
                file_info["status"] = "success"
                print(f"      💾 파일 저장 완료: {file_path}")
            
            if file_path.exists():
                file_info["size"] = os.path.getsize(file_path)
                print(f"      📊 파일 크기: {file_info['size']} bytes")
            
        except Exception as e:
            print(f"      ❌ 파일 저장 중 에러: {str(e)}")
            file_info["status"] = "error"
            file_info["error"] = str(e)
            
        saved_files[filename] = file_info
     

    # 6. 전체 응답 백업
    backup_path = bot_dir / "full_response_backup.txt"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(llm_response)
    print(f"💾 전체 응답 백업: {backup_path}")

    print("\n" + "="*80)
    print("✅ save_bot_design_files 완료!")
    print(f"   총 {len(saved_files)}개 파일 처리됨")
    for fname, finfo in saved_files.items():
        status_emoji = "✅" if finfo["status"] == "success" else "⚠️" if finfo["status"] == "warning" else "❌"
        print(f"   {status_emoji} {fname}: {finfo['status']}")
    print("="*80)

    return {
        "saved_files": saved_files,
        "step3_json": step3_json  # ✅ 반환!
    }


def print_save_results(saved_files: dict):
    """
    저장 결과를 보기 좋게 출력
    
    Args:
        saved_files: save_bot_design_files가 반환한 딕셔너리
    """
    print("\n" + "="*60)
    print("📁 파일 저장 결과")
    print("="*60)
    
    for filename, info in saved_files.items():
        if info["status"] == "success":
            size_kb = info["size"] / 1024
            print(f"✅ {filename}")
            print(f"   경로: {info['path']}")
            print(f"   크기: {size_kb:.2f} KB")
        elif info["status"] == "warning":
            size_kb = info["size"] / 1024
            print(f"⚠️  {filename}")
            print(f"   경로: {info['path']}")
            print(f"   경고: {info['error']}")
            print(f"   크기: {size_kb:.2f} KB")
        elif info["status"] == "not_found":
            print(f"⚠️  {filename}")
            print(f"   {info['error']}")
        else:
            print(f"❌ {filename}")
            print(f"   에러: {info['error']}")
        print()



def apply_modification_with_llm(current_design: dict, modification_request: str) -> dict:
    """
    사용자의 자연어 수정 요청을 LLM으로 해석하여 봇 설계를 수정
    
    Args:
        current_design: 현재 봇 설계 딕셔너리
        modification_request: 사용자의 수정 요청 (예: "전화번호 필드 빼줘")
    
    Returns:
        수정된 봇 설계 딕셔너리
    """
    
    prompt = f"""당신은 챗봇 설계 수정 전문가입니다.

**현재 봇 설계:**
```json
{json.dumps(current_design, ensure_ascii=False, indent=2)}
```

**사용자의 수정 요청:**
"{modification_request}"

**당신의 작업:**
위 수정 요청을 분석하여 봇 설계를 수정해주세요.

**가능한 수정 유형:**
1. 필드 추가/삭제/수정
2. 서비스 봇 추가/삭제/수정
3. 봇 이름 변경
4. 목적(goal) 수정
5. 필드 속성 변경 (필수/선택, 수집 방법 등)

**규칙:**
- 사용자 요청을 정확히 반영하세요
- 봇 설계의 일관성을 유지하세요
- 필드 추가 시 field_name은 영문 snake_case로
- 서비스 봇 추가 시 적절한 bot_type과 role을 설정하세요
- member_id 필드는 절대 삭제하지 마세요

**응답 형식 (JSON만):**
{{
  "main_bot": {{
    "bot_id": "...",
    "name_suggestions": ["...", "...", "..."],
    "goal": "...",
    "fields": [...]
  }},
  "service_bots": [...]
}}"""
    
    # 기존 send_llm_request_xml 사용
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    llm_response_text = send_llm_request_xml(messages,botjob=True, use_hf=True)
    
    # JSON 파싱
    content = llm_response_text
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    return json.loads(content)

# def generate_complete_bot_design_pre(room_id: str, category_id: str, category_title: str = None, user_description: str = None):
#     """
#     LLM을 사용하여 3단계 중간 결과(intermediate_step 1~3)만 생성
#     """
#     api_id = f"{room_id}_{uuid.uuid4().hex[:8]}"


#     if user_description:
#         context = f'사용자가 "{user_description}" 봇을 만들고 싶어합니다.'
#     else:
#         context = f'사용자가 "{category_title}" 카테고리의 봇을 만들고 싶어합니다.'
    
#     prompt = f"""당신은 챗봇 시스템 설계 전문가입니다.

# {context}

# **당신의 임무:**
# 아래 3단계를 **순차적으로** 수행하고, 각 단계의 결과를 JSON으로 출력하세요.

# ---

# ## 📋 1단계: 분류별 옵션 생성 및 랜덤 선택

# **임무:**
# 1. 이 봇을 구체화하기 위해 **5가지 분류**를 만드세요
# 2. 각 분류마다 **3-5개의 세부 옵션**을 나열하세요
# 3. 각 분류에서 **랜덤으로 1개씩** 선택하세요


# **🎯 카테고리 반영 필수!**
# - 카테고리: "{category_title}"
# - 이 카테고리의 핵심 목적을 모든 기능에 반드시 반영하세요
# - 예시:
#   - "쿠폰/이벤트" → 모든 기능이 쿠폰 발급, 할인, 이벤트 참여와 연결
#   - "여행 및 맛집" → 모든 기능이 여행 추천, 맛집 찾기와 연결
#   - "육아" → 모든 기능이 아이 돌봄, 육아 정보와 연결

# **출력 형식:**
# <<<STEP1_START>>>
# ```json
# {{
#   "step": 1,
#   "description": "5가지 분류 및 각 분류별 세부 옵션",
#   "category": "{category_title if category_title else '사용자 정의'}",
#   "user_description": "{user_description if user_description else ''}",
#   "classifications": [
#     {{
#       "category_id": "c1",
#       "category_name": "분류명1",
#       "options": [
#         {{"option_id": "c1_o1", "value": "옵션1"}},
#         {{"option_id": "c1_o2", "value": "옵션2"}},
#         {{"option_id": "c1_o3", "value": "옵션3"}}
#       ],
#       "selected": {{"option_id": "c1_o2", "value": "옵션2"}}
#     }},
#     {{
#       "category_id": "c2",
#       "category_name": "분류명2",
#       "options": [
#         {{"option_id": "c2_o1", "value": "옵션1"}},
#         {{"option_id": "c2_o2", "value": "옵션2"}},
#         {{"option_id": "c2_o3", "value": "옵션3"}},
#         {{"option_id": "c2_o4", "value": "옵션4"}}
#       ],
#       "selected": {{"option_id": "c2_o3", "value": "옵션3"}}
#     }},
#     {{
#       "category_id": "c3",
#       "category_name": "분류명3",
#       "options": [
#         {{"option_id": "c3_o1", "value": "옵션1"}},
#         {{"option_id": "c3_o2", "value": "옵션2"}},
#         {{"option_id": "c3_o3", "value": "옵션3"}}
#       ],
#       "selected": {{"option_id": "c3_o1", "value": "옵션1"}}
#     }},
#     {{
#       "category_id": "c4",
#       "category_name": "분류명4",
#       "options": [
#         {{"option_id": "c4_o1", "value": "옵션1"}},
#         {{"option_id": "c4_o2", "value": "옵션2"}},
#         {{"option_id": "c4_o3", "value": "옵션3"}},
#         {{"option_id": "c4_o4", "value": "옵션4"}},
#         {{"option_id": "c4_o5", "value": "옵션5"}}
#       ],
#       "selected": {{"option_id": "c4_o2", "value": "옵션2"}}
#     }},
#     {{
#       "category_id": "c5",
#       "category_name": "분류명5",
#       "options": [
#         {{"option_id": "c5_o1", "value": "옵션1"}},
#         {{"option_id": "c5_o2", "value": "옵션2"}},
#         {{"option_id": "c5_o3", "value": "옵션3"}},
#         {{"option_id": "c5_o4", "value": "옵션4"}}
#       ],
#       "selected": {{"option_id": "c5_o4", "value": "옵션4"}}
#     }}
#   ],
#   "selected_context_summary": {{
#     "분류명1": "선택된값1",
#     "분류명2": "선택된값2",
#     "분류명3": "선택된값3",
#     "분류명4": "선택된값4",
#     "분류명5": "선택된값5"
#   }},
#   "reselection_guide": "봇 수정 시 위 분류의 다른 옵션을 선택하면 다른 봇이 생성됩니다"
# }}
# ```
# <<<STEP1_END>>>

# ---

# ## 📋 2단계: 서비스 직원 봇 역할 20가지 나열 및 랜덤 선택

# ### 🎯 핵심 개념: 봇 = 실제 직원을 대신함

# **상황:**
# 당신은 "{{category_title}}" 서비스를 운영하는 **방장(사업주)**입니다.
# 고객에게 서비스를 제공하기 위해 **직원을 채용**해야 합니다.
# 하지만 사람 대신 **봇(AI 직원)**을 고용하려고 합니다.

# **봇의 정체:**
# - 실제 매장/서비스 현장에 있는 **직원**
# - 특정 **직무**를 수행하는 전문 인력
# - 고객과 대화하며 **서비스를 제공**

# **봇이 아닌 것:**
# - 자동화 시스템 (자동 발급, 자동 추천)
# - 검색 엔진 (정보 조회)
# - 알림 도구 (푸시 알림)

# ---

# ### 📝 임무

# **1단계 선택 조건**을 반영하여, 
# 해당 서비스 현장에서 일할 **직원 봇 역할 20가지**를 나열하세요.

# 각 봇은 **실제 존재하는 직업/직무**를 담당해야 합니다.

# ---

# ### 🎯 직업군 예시 (서비스별)

# #### 여행/관광 서비스
# **실제 직원들:**
# - 여행 가이드 (투어 안내)
# - 투어 코디네이터 (일정 조율)
# - 현지 가이드 (지역 전문가)
# - 여행사 직원 (예약 접수)
# - 공항 안내원 (공항 서비스)
# - 호텔 컨시어지 (숙박 서비스)
# - 렌터카 상담원 (차량 대여)
# - 액티비티 강사 (체험 지도)

# #### 쇼핑/리테일 서비스
# **실제 직원들:**
# - 매장 판매원 (상품 판매)
# - MD (상품 기획자)
# - 스타일리스트 (코디 조언)
# - 피팅 도우미 (사이즈 상담)
# - 매장 점장 (고객 관리)
# - 재고 관리자 (재입고 안내)
# - VIP 담당자 (단골 고객 관리)
# - 교환/환불 담당자 (AS 처리)

# #### 식음료 서비스
# **실제 직원들:**
# - 주문 접수원 (주문 받기)
# - 소믈리에 (와인 추천)
# - 바리스타 (커피 추천)
# - 영양사 (식단 조언)
# - 셰프 (메뉴 설명)
# - 홀 매니저 (테이블 관리)
# - 배달 기사 (배달 조율)

# #### 쿠폰/이벤트 서비스
# **실제 직원들:**
# - 프로모션 매니저 (이벤트 안내)
# - 할인 상담원 (쿠폰 설명)
# - 멤버십 담당자 (포인트 관리)
# - 이벤트 기획자 (참여 유도)
# - 고객 응대원 (문의 응답)
# - 혜택 안내원 (할인 정보 제공)

# #### 육아 서비스
# **실제 직원들:**
# - 육아 도우미 (돌봄 조언)
# - 보육교사 (발달 상담)
# - 소아과 간호사 (건강 조언)
# - 영양사 (이유식 상담)
# - 놀이 선생님 (놀이 지도)
# - 육아 용품 판매원 (제품 추천)

# ---

# ### 📋 출력 형식

# 각 봇은 다음 정보를 포함:
# ```json
# {{
#   "feature_id": "f001",
#   "name": "{{직업명}} ({{담당 업무}})",
#   "job_title": "{{실제 직업명}}",
#   "description": "{{이 직원이 고객에게 제공하는 서비스}}",
#   "user_value": "{{고객이 얻는 가치}}",
#   "work_scenario": "{{실제 업무 시나리오}}",
#   "complexity": "low|medium|high",
#   "estimated_api_calls": 2
# }}
# ```

# ---

# ### 🚨 필수 규칙

# #### ✅ 반드시 포함

# **1. 실제 존재하는 직업명**
# - "여행 가이드", "매장 판매원", "소믈리에", "호텔 컨시어지"
# - ❌ "최적화 전문가", "컨설턴트", "코치" 같은 추상적 이름

# **2. 구체적인 직무 설명**
# - 이 직원이 **실제로 하는 일**
# - 예: "고객의 체형을 보고 어울리는 옷 사이즈와 스타일을 추천"

# **3. 대화형 서비스**
# - 고객과 질문/답변하며 서비스 제공
# - 예: "어떤 스타일 선호하세요?" → "그럼 이 옷이 잘 어울리겠네요"

# **4. 1단계 조건 모두 반영**
# - 5가지 선택 조건을 모든 직원에 적용

# ---

# #### ❌ 절대 금지

# **자동화 시스템:**
# - ❌ "자동 발급", "자동 추천", "자동 매칭"

# **검색/필터 도구:**
# - ❌ "최적 검색", "조건별 필터링"

# **알림 시스템:**
# - ❌ "만료 알림", "푸시 알림"

# **추상적 직업:**
# - ❌ "전문가", "컨설턴트", "상담사", "코치"
# - ✅ "판매원", "가이드", "매니저", "직원"

# ---

# ### 📝 구체적 예시

# #### 예시 1: 쿠폰/이벤트 + 제주도 숙박

# **❌ 나쁜 예시:**
# ```json
# {{
#   "name": "제주도 쿠폰 최적화 전문가",
#   "job_title": "최적화 전문가",
#   "why_bad": "실제 존재하는 직업 아님, 추상적"
# }}
# ```

# **✅ 좋은 예시 1:**
# ```json
# {{
#   "feature_id": "f001",
#   "name": "제주도 숙박 프로모션 매니저",
#   "job_title": "프로모션 매니저",
#   "description": "호텔/펜션의 현재 진행 중인 이벤트와 할인 쿠폰을 고객 상황에 맞게 설명하고, 어떤 쿠폰을 언제 사용하면 가장 이득인지 안내합니다. 마치 호텔 프론트에서 고객에게 '지금 이 쿠폰 쓰시면 더 저렴해요'라고 알려주는 것처럼 동작합니다.",
#   "user_value": "직원이 직접 알려주는 것처럼 숨은 할인 혜택 확보",
#   "work_scenario": "고객: 3박 예약하고 싶어요 → 매니저: 지금 4박 하시면 1박 무료 이벤트 중이에요. 예산이 어떻게 되세요? → 맞춤 제안",
#   "complexity": "medium",
#   "estimated_api_calls": 3
# }}
# ```

# **✅ 좋은 예시 2:**
# ```json
# {{
#   "feature_id": "f002",
#   "name": "제주도 현지 여행 가이드",
#   "job_title": "현지 가이드",
#   "description": "제주도에서 10년 일한 현지 가이드처럼, 고객의 여행 일정과 예산을 듣고 숙박지 근처의 숨은 맛집, 할인받을 수 있는 액티비티, 현지인만 아는 이벤트 정보를 알려줍니다.",
#   "user_value": "현지 가이드 수준의 인사이트로 여행 만족도 2배 상승",
#   "work_scenario": "고객: 서귀포 쪽 펜션 잡았어요 → 가이드: 그럼 차로 5분 거리에 해산물 직판장 있는데 거기 쿠폰 쓰면 30% 할인돼요",
#   "complexity": "high",
#   "estimated_api_calls": 4
# }}
# ```

# **✅ 좋은 예시 3:**
# ```json
# {{
#   "feature_id": "f003",
#   "name": "숙박 시설 멤버십 담당자",
#   "job_title": "멤버십 담당자",
#   "description": "호텔 체인의 멤버십 담당 직원처럼, 고객의 포인트 현황을 보고 '이번에 포인트 쌓으실래요, 아니면 할인 받으실래요?', '다음 달에 또 오시면 무료 업그레이드 가능해요' 같은 맞춤 조언을 제공합니다.",
#   "user_value": "포인트 전략으로 장기적으로 50만원 이상 절감",
#   "work_scenario": "고객: 포인트가 5만점 있어요 → 담당자: 지금 쓰면 3만원 할인이고, 모으면 다음에 무료 숙박이에요. 언제 또 오세요?",
#   "complexity": "medium",
#   "estimated_api_calls": 3
# }}
# ```

# **✅ 좋은 예시 4:**
# ```json
# {{
#   "feature_id": "f004",
#   "name": "여행사 패키지 상담 직원",
#   "job_title": "여행사 직원",
#   "description": "여행사 창구 직원처럼, 고객의 예산과 일정을 듣고 '숙박+렌터카+액티비티'를 묶은 패키지 상품을 제안하며, 개별 구매 vs 패키지 중 어느 쪽이 저렴한지 계산해서 보여줍니다.",
#   "user_value": "여행사 직원 수준의 패키지 설계로 20% 비용 절감",
#   "work_scenario": "고객: 100만원 예산이에요 → 직원: 패키지로 하면 85만원에 다 되는데, 렌터카는 따로 하시겠어요?",
#   "complexity": "high",
#   "estimated_api_calls": 5
# }}
# ```

# ---

# #### 예시 2: 쇼핑 + 의류

# **✅ 좋은 예시:**
# ```json
# {{
#   "feature_id": "f001",
#   "name": "매장 스타일리스트",
#   "job_title": "스타일리스트",
#   "description": "백화점 명품관 스타일리스트처럼, 고객의 체형, 피부톤, 선호 스타일을 듣고 어울리는 옷을 골라주고 코디를 제안합니다.",
#   "work_scenario": "고객: 결혼식 갈 옷 찾아요 → 스타일리스트: 체형이 어떻게 되세요? 어떤 색 좋아하세요?",
#   "complexity": "high",
#   "estimated_api_calls": 4
# }}
# ```
# ```json
# {{
#   "feature_id": "f002",
#   "name": "매장 판매 사원",
#   "job_title": "판매 사원",
#   "description": "옷 가게 판매원처럼, 고객이 고른 옷의 사이즈가 맞는지 확인하고, 비슷한 스타일의 다른 상품도 함께 추천하며, 지금 할인 중인 제품을 알려줍니다.",
#   "work_scenario": "고객: 이 청바지 있어요? → 판매원: 55사이즈 재고 있어요. 혹시 상의도 보실래요? 지금 세트로 사면 20% 할인이에요",
#   "complexity": "medium",
#   "estimated_api_calls": 3
# }}
# ```

# ---

# #### 예시 3: 육아 + 이유식

# **✅ 좋은 예시:**
# ```json
# {{
#   "feature_id": "f001",
#   "name": "소아 영양사",
#   "job_title": "영양사",
#   "description": "병원 소아과 영양사처럼, 아기 개월 수와 알레르기 여부를 듣고 적합한 이유식 재료와 조리법을 추천하며, 영양 균형을 맞추는 방법을 알려줍니다.",
#   "work_scenario": "부모: 6개월 아기인데 뭐 먹여야 해요? → 영양사: 알레르기 있나요? 그럼 쌀미음부터 시작하세요",
#   "complexity": "high",
#   "estimated_api_calls": 4
# }}
# ```
# ```json
# {{
#   "feature_id": "f002",
#   "name": "육아 용품 판매 사원",
#   "job_title": "판매 사원",
#   "description": "육아 용품 매장 직원처럼, 부모의 필요(예: 외출용 유모차, 집에서 쓸 바운서)를 듣고 예산에 맞는 제품을 추천하며, 지금 할인 중인 상품을 안내합니다.",
#   "work_scenario": "부모: 유모차 사려고요 → 판매원: 주로 어디서 쓰세요? 예산은요? 지금 이 모델 30% 할인 중이에요",
#   "complexity": "medium",
#   "estimated_api_calls": 3
# }}
# ```

# ---

# ### 🎯 20개 직원 봇 생성 시 주의사항

# **1. 다양한 직무 분산**
# - 같은 직업 반복 X
# - 예: 판매원 10개 (X) → 판매원, MD, 스타일리스트, 피팅 도우미, 점장 등 (O)

# **2. 고객 접점 직원 우선**
# - 고객과 직접 대화하는 직원
# - 예: 판매원 (O), 재고 관리자 (△)

# **3. 실제 현장 직무**
# - 실제 매장/서비스 현장에 존재하는 직업
# - 예: 스타일리스트 (O), AI 추천 엔진 (X)

# ---

# ### 📋 최종 출력 형식

# <<<STEP2_START>>>
# ```json
# {{
#   "step": 2,
#   "description": "선택된 조건에 맞는 서비스 직원 봇 역할 20가지",
#   "category": "{{category_title}}",
#   "based_on_context": {{
#     "분류명1": "선택된값1",
#     "분류명2": "선택된값2",
#     "분류명3": "선택된값3",
#     "분류명4": "선택된값4",
#     "분류명5": "선택된값5"
#   }},
#   "employee_bots": [
#     {{
#       "feature_id": "f001",
#       "name": "{{직업명}} ({{담당 업무}})",
#       "job_title": "{{실제 직업명}}",
#       "description": "{{이 직원이 고객에게 제공하는 서비스}}",
#       "user_value": "{{고객이 얻는 가치}}",
#       "work_scenario": "{{실제 업무 시나리오}}",
#       "complexity": "medium",
#       "estimated_api_calls": 3
#     }}
#     (f002 ~ f020까지 20개)
#   ],
#   "selected_feature": {{
#     "feature_id": "f008",
#     "name": "선택된 직원 봇 이름",
#     "job_title": "선택된 직업명",
#     "description": "설명",
#     "user_value": "가치",
#     "work_scenario": "시나리오",
#     "complexity": "medium",
#     "estimated_api_calls": 3
#   }},
#   "reselection_guide": "봇 수정 시 위 20개 직원 중 다른 것을 선택하면 완전히 다른 봇이 생성됩니다"
# }}
# ```
# <<<STEP2_END>>>
# ---
# ## 📋 3단계: 직원 업무 프로세스 설계 및 변수 분류 (3-Phase)

# ### 🎯 핵심 개념

# **이 단계의 목적:**
# "{{selected_function.name}}" 직원이 고객에게 서비스를 제공하는 **전체 업무 프로세스**를 설계하고,
# 각 단계에서 **어떤 정보가 필요한지** 파악한 후, **변수로 분류**합니다.

# **사고 방식:**
# 당신이 실제로 이 직원이라고 상상하세요.
# 고객이 와서 서비스를 요청하면, **시작부터 완료까지 어떤 단계를 거치나요?**

# ---

# ### 📋 Phase 1: 업무 프로세스 설계 (직원 관점)

# **질문: "{{selected_function.name}}" 직원이 고객에게 서비스를 제공하는 전체 과정은 무엇인가요?**

# #### Step 1: 서비스 유형 파악

# 먼저 이 서비스가 어떤 유형인지 판단하세요:

# **A. 예약/약속형 서비스**
# - 예: 여행 가이드, 강사, 컨시어지, 상담원
# - 특징: 시간, 장소, 일정 조율 필요
# - 프로세스: 니즈 파악 → 일정 조율 → 장소 확정 → 조건 확인 → 예약 확정 → 서비스 제공

# **B. 즉시 처리형 서비스**
# - 예: 매장 판매원, 주문 접수원, 고객 응대원
# - 특징: 즉시 상담/판매, 재고 확인, 결제
# - 프로세스: 니즈 파악 → 상품 추천 → 재고 확인 → 시착/체험 → 결제 → 포장/배송

# **C. 분석/검토형 서비스**
# - 예: 상품 MD, 안전 점검관, 품질 관리자
# - 특징: 데이터 분석, 조건 검토, 보고서 작성
# - 프로세스: 대상 확인 → 항목 리스트 → 현장 조사 → 데이터 수집 → 분석 → 보고서 → 전달

# **D. 배송/물류형 서비스**
# - 예: 배달 기사, 배송 담당자
# - 특징: 주소, 배송 시간, 배송 상태
# - 프로세스: 주문 접수 → 상품 준비 → 배송지 확인 → 배송 → 수령 확인

# **E. 지속 관리형 서비스**
# - 예: 멤버십 담당자, 고객 관리자
# - 특징: 장기 관계, 주기적 소통
# - 프로세스: 고객 등록 → 니즈 분석 → 혜택 제공 → 주기적 소통 → 만족도 관리

# ---

# #### Step 2: 업무 프로세스 단계별 분해

# **프로세스 설계 원칙:**

# 모든 서비스는 **3단계 구조**를 따릅니다:

# **A단계: 기본 정보 수집**
# - 사용자 입력: 날짜, 인원, 예산 등
# - 목적: 무엇을 원하는지 파악

# **B단계: 옵션 조회 및 선택** (← **매우 중요!**)
# - 정보 조회용 API 호출 (서브봇)
# - 옵션을 사용자에게 제시
# - **사용자가 선택** (사용자 입력!)
# - 필요시 추가 정보 수집

# **C단계: 최종 실행**
# - 모든 정보가 모였음
# - **최종 Webhook 호출**
# - 서비스 완료!

# ---

# **중요한 차이:**

# ❌ **잘못된 프로세스:**
# ```
# A. 정보 수집 → B. API 호출 → 끝
# ```

# ✅ **올바른 프로세스:**
# ```
# A. 정보 수집 → B. 조회 API → 사용자 선택 → C. 최종 Webhook
# ```

# ---

# **구체적 예시:**

# **예시 1: 예약/약속형 - 리조트 컨시어지**
# ```
# step1: 고객 니즈 파악 (A단계)
#   - action: 체크인/체크아웃 날짜, 인원 확인
#   - purpose: 기본 조건 파악
#   - required_info: [check_in_date, check_out_date, number_of_guests]

# step2: 객실 타입 선호 확인 (A단계)
#   - action: 어떤 타입의 객실을 선호하는지 질문
#   - purpose: 고객 취향 파악
#   - required_info: [room_type_preference, budget]

# step3: 가용 객실 조회 (B단계 - 조회)
#   - action: 조건에 맞는 가용 객실을 API로 조회
#   - purpose: 실제 예약 가능한 방 확인
#   - required_info: [available_rooms] ← 서브봇이 API 호출

# step4: 객실 옵션 제시 및 선택 (B단계 - 선택) ← **핵심!**
#   - action: 조회된 객실들을 고객에게 보여주고 선택 유도
#   - purpose: 고객이 원하는 방 확정
#   - required_info: [selected_room_id] ← **사용자 입력!**
#   - 예: "101호 스위트(15만원)와 203호 델럭스(10만원)가 있어요. 어느 방 원하세요?"

# step5: 추가 정보 수집 (B단계)
#   - action: 결제 방법, 특별 요청사항 확인
#   - purpose: 예약 완료에 필요한 세부 정보
#   - required_info: [payment_method, special_requests]

# step6: 고객 정보 확인 (B단계)
#   - action: 예약자 이름, 연락처 확인
#   - purpose: 예약 확정 및 연락
#   - required_info: [customer_name, customer_phone]

# step7: 예약 확정 (C단계) ← **최종 Webhook**
#   - action: 모든 정보를 최종 Webhook으로 전송
#   - purpose: 실제 예약 완료
#   - webhook_call: POST /api/{{api_id}}
#   - 결과: reservation_id 발급

# step8: 체크인 안내 (C단계 후)
#   - action: 체크인 시간, 위치 안내
#   - purpose: 고객 편의
# ```

# **예시 2: 즉시 처리형 - 의류 매장 판매원**
# ```
# step1: 고객 니즈 파악 (A단계)
#   - action: 어떤 옷을 찾는지 질문
#   - purpose: 고객 취향 파악
#   - required_info: [product_type, purpose, budget]

# step2: 고객 정보 수집 (A단계)
#   - action: 체형, 선호 색상, 스타일 확인
#   - purpose: 맞춤 추천
#   - required_info: [body_type, preferred_color, preferred_style]

# step3: 재고 조회 (B단계 - 조회)
#   - action: 조건에 맞는 상품 재고 API 호출
#   - purpose: 구매 가능 상품 확인
#   - required_info: [available_products] ← 서브봇이 API 호출

# step4: 상품 제시 및 선택 (B단계 - 선택) ← **핵심!**
#   - action: 재고 있는 상품들을 보여주고 선택 유도
#   - purpose: 고객이 원하는 상품 확정
#   - required_info: [selected_product_id] ← **사용자 입력!**
#   - 예: "이 셔츠(5만원)와 저 재킷(8만원)이 있어요. 어떤 걸 원하세요?"

# step5: 사이즈 선택 (B단계)
#   - action: 사이즈 확인 및 선택
#   - purpose: 맞는 사이즈 확정
#   - required_info: [selected_size]

# step6: 시착 지원 (B단계)
#   - action: 피팅룸 안내 및 확인
#   - purpose: 구매 전 최종 확인
#   - required_info: [fitting_result]

# step7: 추가 상품 제안 (B단계)
#   - action: 코디 가능한 다른 상품 추천
#   - purpose: 추가 판매
#   - required_info: [additional_items]

# step8: 결제 진행 (C단계) ← **최종 Webhook**
#   - action: 결제 방법 확인 및 최종 Webhook 호출
#   - purpose: 구매 완료
#   - webhook_call: POST /api/{{api_id}}
#   - 결과: order_id 발급

# step9: 포장 및 안내
#   - action: 상품 포장, 교환/환불 정책 안내
#   - purpose: 구매 완료
# ```

# **예시 3: 분석/검토형 - 안전 점검관**
# ```
# step1: 점검 대상 확인 (A단계)
#   - action: 어떤 시설을 점검하는지 확인
#   - purpose: 점검 범위 파악
#   - required_info: [facility_name, facility_address, facility_type]

# step2: 점검 항목 조회 (B단계 - 조회)
#   - action: 시설 유형에 맞는 점검 항목 API 조회
#   - purpose: 점검 체크리스트 확보
#   - required_info: [inspection_checklist] ← 서브봇이 API 호출

# step3: 점검 일정 조율 (A단계)
#   - action: 현장 방문 가능 날짜/시간 확인
#   - purpose: 점검 스케줄 확정
#   - required_info: [inspection_date, inspection_time]

# step4: 현장 접근 정보 (A단계)
#   - action: 담당자 연락처, 접근 방법 확인
#   - purpose: 원활한 현장 조사
#   - required_info: [contact_person, contact_phone, access_method]

# step5: 현장 점검 수행 (서비스 실행 - 오프라인)
#   - action: 실제 시설 점검
#   - purpose: 데이터 수집
#   - required_info: [measurement_data, photos, risk_factors]

# step6: 점검 항목별 결과 입력 (B단계)
#   - action: 각 항목의 합격/불합격 입력
#   - purpose: 점검 결과 기록
#   - required_info: [inspection_results]

# step7: 종합 위험도 평가 (B단계)
#   - action: 전체 점검 결과를 바탕으로 등급 판정
#   - purpose: 안전 등급 결정
#   - required_info: [overall_grade, critical_issues]

# step8: 보고서 제출 (C단계) ← **최종 Webhook**
#   - action: 모든 점검 결과를 최종 Webhook으로 전송
#   - purpose: 공식 보고서 생성
#   - webhook_call: POST /api/{{api_id}}
#   - 결과: report_id 발급

# step9: 결과 전달 및 후속 조치
#   - action: 담당자에게 보고서 전달, 재점검 일정 안내
#   - purpose: 개선 조치 유도
# ```

# **예시 4: 배송/물류형 - 온라인 쇼핑몰 배송 담당자**
# ```
# step1: 주문 정보 확인 (A단계)
#   - action: 주문 번호로 주문 내역 조회
#   - purpose: 배송할 상품 확인
#   - required_info: [order_id, product_list]

# step2: 배송지 정보 수집 (A단계)
#   - action: 배송 주소, 수령인 정보 확인
#   - purpose: 정확한 배송
#   - required_info: [delivery_address, recipient_name, recipient_phone]

# step3: 배송 가능 일시 조회 (B단계 - 조회)
#   - action: 배송 가능한 날짜/시간대 API 조회
#   - purpose: 배송 스케줄 확인
#   - required_info: [available_delivery_slots] ← 서브봇이 API 호출

# step4: 배송 일시 선택 (B단계 - 선택) ← **핵심!**
#   - action: 가능한 배송 시간대를 보여주고 선택 유도
#   - purpose: 고객 편의에 맞는 배송
#   - required_info: [selected_delivery_date, selected_delivery_time] ← **사용자 입력!**
#   - 예: "내일 오전, 내일 오후, 모레 오전 중 언제가 좋으세요?"

# step5: 특별 요청 확인 (B단계)
#   - action: 배송 시 주의사항, 문 앞 배송 여부 등 확인
#   - purpose: 맞춤 배송
#   - required_info: [delivery_note, leave_at_door]

# step6: 배송 신청 (C단계) ← **최종 Webhook**
#   - action: 모든 배송 정보를 최종 Webhook으로 전송
#   - purpose: 배송 시작
#   - webhook_call: POST /api/{{api_id}}
#   - 결과: delivery_id, tracking_number 발급

# step7: 배송 진행
#   - action: 실제 배송 수행
#   - purpose: 상품 전달

# step8: 수령 확인
#   - action: 고객 수령 확인
#   - purpose: 배송 완료
# ```

# ---

# #### Step 3: 각 단계별 필요 정보 추출

# **정보 추출 프로세스:**

# 1. **workflow의 각 step 검토**
#    - 모든 step의 required_info를 수집

# 2. **중복 제거**
#    - 여러 step에서 중복되는 정보는 하나로 통합

# 3. **구체화**
#    - 모호한 정보는 세분화
#    - 예: "시간" → "시작 시간", "종료 시간"

# 4. **선택 변수 추가** ← **매우 중요!**
#    - 조회 API 결과가 **목록/배열**이면
#    - 반드시 **선택 변수**가 필요!
#    - 예: available_rooms → selected_room_id
#    - 예: available_products → selected_product_id
#    - 예: available_dates → selected_date

# 5. **최종 리스트 작성**
#    - total_info_needed로 정리

# ---

# **정보 카테고리 예시 (참고용, 해당되는 것만 선택):**

# **예시 A: 고객 식별 정보**
# - 예: 이름, 연락처, 이메일, 회원번호, 나이, 성별

# **예시 B: 서비스/상품 정보**
# - 예: 상품명, 서비스 종류, 옵션, 수량, 규모, 난이도, 레벨

# **예시 C: 시간 관련 정보** (시간이 중요한 서비스)
# - 예: 희망 날짜, 시작 시간, 종료 시간, 소요 시간, 요일

# **예시 D: 장소 관련 정보** (장소가 중요한 서비스)
# - 예: 주소, GPS 좌표, 지역, 만남 장소, 배송 주소

# **예시 E: 인원 관련 정보** (그룹 서비스)
# - 예: 참여 인원, 연령대, 단독/그룹 여부

# **예시 F: 준비물/조건** (특수 요구사항)
# - 예: 필요 장비, 사전 준비물, 제한 사항, 알레르기, 특이사항

# **예시 G: 비용 관련 정보**
# - 예: 가격, 할인율, 쿠폰 코드, 결제 방법, 선결제/후불

# **예시 H: 확인/동의 사항**
# - 예: 약관 동의, 취소 정책 확인, 개인정보 수집 동의, 환불 정책

# **예시 I: 배송/물류 정보** (배송 서비스)
# - 예: 배송 주소, 수령인, 희망 배송일, 배송 메모

# **예시 J: 분석/검토 정보** (분석 서비스)
# - 예: 점검 대상, 점검 항목, 측정값, 위험도

# **예시 K: 조회 결과 및 선택** ← **매우 중요!**
# - 조회 결과: available_rooms, available_products, available_dates
# - **선택 결과: selected_room_id, selected_product_id, selected_date**

# **예시 L: 피드백/평가 정보**
# - 예: 만족도, 리뷰, 개선 요청사항

# ---

# **중요:**
# - 위 예시는 **참고용**입니다
# - 해당 서비스에 **실제로 필요한 정보만** 선택하세요
# - 예시에 없는 정보도 **자유롭게 추가**하세요

# ---


# ### 📋 Phase 1 출력

# <<<BUSINESS_PLAN_START>>>
# ```json
# {{
#   "employee_role": "{{selected_function.name}}",
#   "job_title": "{{selected_function.job_title}}",
#   "service_type": "예약/약속형|즉시처리형|분석/검토형|배송/물류형|지속관리형",
#   "final_goal": "이 서비스의 최종 목적 (예: 객실 예약 확정, 상품 구매 완료, 보고서 제출)",
  
#   "service_workflow": {{
#     "step1": {{
#       "action": "구체적 행동",
#       "purpose": "왜 필요한가",
#       "stage": "A|B|C",
#       "required_info": ["정보1", "정보2"]
#     }},
#     "step2": {{
#       "action": "구체적 행동",
#       "purpose": "왜 필요한가",
#       "stage": "A|B|C",
#       "required_info": ["정보1", "정보2"]
#     }}
#     ... (서비스 특성에 맞게 5-10단계, 반드시 B단계에 선택 과정 포함)
#   }},
  
#   "total_info_needed": [
#     "고객 기본 정보들 (A단계)",
#     "조회 API 결과 (B단계)",
#     "사용자 선택 결과 (B단계) ← 매우 중요!",
#     "추가 세부 정보 (B단계)",
#     ... (최소 8개 이상)
#   ]
# }}
# ```
# <<<BUSINESS_PLAN_END>>>

# ---





# ### 📋 Phase 2: 최종 Webhook 요청 데이터 설계

# **API Endpoint:**
# - 고유 API ID: `{api_id}`
# - 전체 경로: `/api/{api_id}`

# **중요: 이것은 서비스를 실제로 실행하는 최종 Webhook입니다**

# 이 Webhook은:
# - 서비스의 **최종 목적**을 달성합니다 (예: 예약 확정, 구매 완료, 보고서 제출)
# - 모든 정보가 **완전히 수집된 후** 호출됩니다 (C단계)
# - 중간 조회용 API가 **아닙니다**

# 예시:
# - 예약 확정 Webhook (GET 아님, POST!)
# - 구매 완료 Webhook
# - 보고서 제출 Webhook
# - 배송 신청 Webhook

# **이 Webhook에 보낼 데이터:**
# - 사용자 입력 (A단계)
# - **사용자 선택 결과 (B단계) ← 매우 중요!**
# - 필요시 조회 API 결과 일부 (B단계)

# **Phase 1의 `total_info_needed`를 기반으로 최종 Webhook 요청 Body를 설계합니다.**

# **설계 원칙:**
# - 각 정보를 적절한 필드명으로 변환 (영문, snake_case)
# - 데이터 타입 지정 (String, Number, Boolean, Date, Time, Array, Object)
# - 예시 값 제공

# **예시:**
# ```json
# POST /api/{api_id}
# {{
#   "check_in_date": "2025-07-10",
#   "check_out_date": "2025-07-13",
#   "number_of_guests": 3,
#   "selected_room_id": "101",  ← 선택 결과!
#   "payment_method": "card",
#   "customer_name": "홍길동",
#   "customer_phone": "010-1234-5678"
# }}
# ```

# ---

# ### 📋 Phase 3: 변수 분류

# Phase 2의 각 필드를 분류합니다.

# **분류 기준:**

# **질문 1: 사용자에게 물어볼 수 있나?**
# - YES → 사용자 입력
# - NO → 질문 2

# **질문 2: 중간에 정보를 조회해야 하나?**
# - YES → 정보 조회용 API (서브봇)

# 예시:
# - 가능한 방 목록 조회
# - 상품 재고 확인
# - 날씨 정보 조회
# - 회원 포인트 확인

# **중요:** 
# - 이건 **중간 단계**입니다 (B단계)
# - 조회한 정보를 사용자에게 보여주고
# - 사용자가 **반드시 선택**해야 합니다
# - 선택 후 → 최종 Webhook 호출 (C단계)

# ---

# **중요 규칙:**
# - ✅ 챗봇이 수집: 사용자 입력 + 정보 조회용 API (원본 데이터만!)
# - ❌ 챗봇이 하지 않음: 계산, 필터링, 검증, 정렬, 최적화, 분석, 저장

# ---

# **변수 작성 패턴:**

# 조회 변수가 **목록/배열**이면, 
# 반드시 **선택 변수**가 필요합니다!

# - available_rooms (API 호출) → selected_room_id (사용자 입력)
# - available_products (API 호출) → selected_product_id (사용자 입력)
# - available_dates (API 호출) → selected_date (사용자 입력)
# - available_times (API 호출) → selected_time (사용자 입력)
# - color_options (API 호출) → selected_color (사용자 입력)

# ---

# ### 서브봇 API Endpoint 생성 규칙

# 각 서브봇은 고유한 API endpoint를 가집니다:

# **형식:**
# ```
# /api/{api_id}_{{sub_bot_id}}
# ```

# **예시:**
# ```json
# {{
#   "variable_name": "available_equipment",
#   "sub_bot_id": "equipment_query_task",
#   "api_endpoint": "/api/lesson_education_b83c61ac_equipment_query_task_a1b2c3d4",
#   "execution_logic": {{
#     "step1": "API 호출: GET /api/equipment?location={{preferred_location}}",
#     "step2": "결과를 available_equipment에 저장",
#     "step3": "사용자에게 옵션 제시",
#     "step4": "completed = true"
#   }}
# }}
# ```
# ```json
# {{
#   "variable_name": "total_amount",
#   "sub_bot_id": "total_calculation_task",
#   "api_endpoint": "/api/lesson_education_b83c61ac_total_calculation_task_e5f6g7h8",
#   "execution_logic": {{
#     "step1": "총액 계산 로직 실행",
#     "step2": "total_amount에 저장",
#     "step3": "completed = true"
#   }}
# }}
# ```

# **중요:**
# - 각 서브봇마다 8자리 랜덤 UUID가 다릅니다
# - {api_id}는 메인 봇의 API ID와 동일합니다
# - {{sub_bot_id}}로 어떤 서브봇인지 식별 가능합니다


# ### 📋 최종 출력 형식

# <<<STEP3_START>>>
# <file>
# <filename>intermediate_step3.json</filename>
# <content>
# ```json
# {{
#   "step": 3,
#   "description": "선택된 기능 실행을 위한 변수 분류",
#   "selected_function": {{
#     "feature_id": "{{Step 2의 feature_id}}",
#     "name": "{{Step 2의 name}}",
#     "job_title": "{{Step 2의 job_title}}",
#     "description": "{{Step 2의 description}}",
#     "user_value": "{{Step 2의 user_value}}",
#     "work_scenario": "{{Step 2의 work_scenario}}"
#   }},
#   "based_on_context": {{
#     "분류명1": "값1",
#     "분류명2": "값2",
#     "분류명3": "값3",
#     "분류명4": "값4",
#     "분류명5": "값5"
#   }},
  
#   "business_plan": {{
#     "service_type": "서비스 유형",
#     "final_goal": "이 서비스의 최종 목적",
#     "service_workflow": {{
#       "step1": {{
#         "action": "행동",
#         "purpose": "목적",
#         "stage": "A|B|C",
#         "required_info": ["정보들"]
#       }}
#       ... (5-10 단계, 반드시 B단계에 선택 과정 포함)
#     }},
#     "total_info_needed": [
#       "정보1",
#       "정보2",
#       ... (최소 8개 이상, 선택 변수 반드시 포함)
#     ]
#   }},
  
#   "webhook_spec": {{
#     "endpoint": "/api/{api_id}",
#     "method": "POST",
#     "description": "서비스 최종 실행을 위한 Webhook"
#   }},
  
#   "all_variables": [
#     {{
#       "variable_id": "v001",
#       "variable_name": "필드명",
#       "description": "설명",
#       "data_type": "String|Number|Boolean|Date|Time|Array|Object",
#       "category": "사용자 입력|API 호출",
#       "example": "예시값",
#       "why_this_category": "분류 이유"
#     }}
#     ... (total_info_needed 개수만큼)
#   ],
  
#   "classification": {{
#     "user_input_variables": [
#       {{
#         "variable_id": "v001",
#         "variable_name": "필드명",
#         "question": "사용자에게 물어볼 질문",
#         "data_type": "타입",
#         "is_mandatory": true|false,
#         "validation_rule": "검증 규칙"
#       }}
#       ...
#     ],
#     "non_user_input_variables": [
#        {{
#     "variable_id": "v00X",
#     "variable_name": "필드명",
#     "sub_bot_id": "서브봇_아이디_task",
#     "sub_bot_name": "서브봇 이름",
#     "api_endpoint": "/api/{api_id}_{{sub_bot_id}}",
#     "purpose": "목적",
#     "trigger_keyword": ["키워드1", "키워드2"],
#     "source": "데이터 출처 (API명 등)",
#     "why_not_ask_user": "사용자에게 물으면 안 되는 이유",
#     "execution_logic": {{
#       "step1": "구체적 실행 단계 (필요 시 API 호출 포함)",
#       "step2": "구체적 실행 단계",
#       "step3": "결과 저장",
#       "step4": "completed = true"
#     }}
#   }}
#       ...
#     ]
#   }},
  
#   "summary": {{
#     "total_variables": 숫자,
#     "user_input_count": 숫자,
#     "non_user_input_count": 숫자,
#     "generated_sub_bots_count": 숫자
#   }},
  
#   "reselection_guide": "변수 분류를 수정하면 메인봇 질문과 서브봇 개수가 변경됩니다"
# }}
# ```
# </content>
# </file>
# <<<STEP3_END>>>

# ---

# ### 🚨 최종 체크리스트

# 생성 전 확인:
# - [ ] selected_function이 Step 2의 모든 필드를 포함하는가?
# - [ ] service_type이 5가지 중 하나로 명확히 선택되었는가?
# - [ ] final_goal이 구체적으로 명시되었는가?
# - [ ] service_workflow가 최소 5단계 이상인가?
# - [ ] workflow에 B단계(옵션 조회 → 선택)가 명확히 포함되어 있는가?
# - [ ] 각 step마다 action, purpose, stage, required_info가 구체적인가?
# - [ ] total_info_needed가 최소 8개 이상인가?
# - [ ] 조회 API 결과(목록)에 대응하는 선택 변수가 있는가?
# - [ ] all_variables가 total_info_needed를 모두 반영하는가?
# - [ ] 사용자 입력 변수가 충분한가? (최소 5개 이상 권장)
# - [ ] 선택 변수(selected_XXX)가 사용자 입력으로 분류되어 있는가?
# - [ ] 비사용자 입력 변수의 execution_logic이 구체적인가?
# - [ ] webhook_spec의 endpoint가 /api/{api_id} 형식인가?
# - [ ] summary의 숫자들이 정확한가?



# ## 📦 파일 생성

# 위 3단계 결과를 각각 파일로 저장하세요.

# **중요: 반드시 아래 XML 형식을 정확히 지켜주세요!**

# <<<STEP1_START>>>
# <file>
# <filename>intermediate_step1.json</filename>
# <content>
# ```json
# {{
#   "step": 1,
#   "description": "5가지 분류 및 각 분류별 세부 옵션",
#   ...
#   (STEP1의 전체 JSON 내용)
# }}
# ```
# </content>
# </file>
# <<<STEP1_END>>>

# <<<STEP2_START>>>
# <file>
# <filename>intermediate_step2.json</filename>
# <content>
# ```json
# {{
#   "step": 2,
#   "description": "선택된 조건에 맞는 서비스 직원 봇 역할 20가지",
#   ...
#   (STEP2의 전체 JSON 내용)
# }}
# ```
# </content>
# </file>
# <<<STEP2_END>>>

# <<<STEP3_START>>>
# <file>
# <filename>intermediate_step3.json</filename>
# <content>
# ```json
# {{
#   "step": 3,
#   "description": "선택된 기능 실행을 위한 변수 분류",
#   ...
#   (STEP3의 전체 JSON 내용)
# }}
# ```
# </content>
# </file>
# <<<STEP3_END>>>

# ---

# **필수 체크:**
# 1. 각 STEP은 <<<STEPN_START>>>와 <<<STEPN_END>>> 사이에 위치
# 2. 각 파일은 <file> 태그로 감싸기
# 3. <filename> 태그에 파일명 명시
# 4. <content> 태그 안에 실제 JSON 내용
# 5. 3개 파일만 생성 (main_task_config.json 등은 만들지 마세요)
# 6. JSON 내용은 완전해야 함 (요약 금지, ... 사용 금지)
# """
    
#     messages = [
#         {"role": "user", "content": prompt}
#     ]
    
#     llm_response_text = send_llm_request_xml(messages, botjob=True, use_hf=True)
    
#     # 파일 저장
#     result  = save_bot_design_files(llm_response_text, category_id)
    
#     return {
#         "raw_response": llm_response_text,
#         "saved_files": result["saved_files"],
#         "step3_json": result["step3_json"]  # ✅ 추가!
#     }


def generate_complete_bot_design_pre(room_id: str, category_id: str, category_title: str = None, user_description: str = None):
    """
    LLM을 사용하여 3단계 중간 결과(intermediate_step 1~3)만 생성
    """
    api_id = f"{room_id}_{uuid.uuid4().hex[:8]}"


    if user_description:
        context = f'사용자가 "{user_description}" 봇을 만들고 싶어합니다.'
    else:
        context = f'사용자가 "{category_title}" 카테고리의 봇을 만들고 싶어합니다.'
    
    prompt = f"""당신은 챗봇 시스템 설계 전문가입니다.

{context}

**당신의 임무:**
아래 3단계를 **순차적으로** 수행하고, 각 단계의 결과를 JSON으로 출력하세요.

---

## 📋 1단계: 분류별 옵션 생성 및 랜덤 선택

**임무:**
1. 이 봇을 구체화하기 위해 **5가지 분류**를 만드세요
2. 각 분류마다 **3-5개의 세부 옵션**을 나열하세요
3. 각 분류에서 **랜덤으로 1개씩** 선택하세요


**🎯 카테고리 반영 필수!**
- 카테고리: "{category_title}"
- 이 카테고리의 핵심 목적을 모든 기능에 반드시 반영하세요
- 예시:
  - "쿠폰/이벤트" → 모든 기능이 쿠폰 발급, 할인, 이벤트 참여와 연결
  - "여행 및 맛집" → 모든 기능이 여행 추천, 맛집 찾기와 연결
  - "육아" → 모든 기능이 아이 돌봄, 육아 정보와 연결

**출력 형식:**
<<<STEP1_START>>>
```json
{{
  "step": 1,
  "description": "5가지 분류 및 각 분류별 세부 옵션",
  "category": "{category_title if category_title else '사용자 정의'}",
  "user_description": "{user_description if user_description else ''}",
  "classifications": [
    {{
      "category_id": "c1",
      "category_name": "분류명1",
      "options": [
        {{"option_id": "c1_o1", "value": "옵션1"}},
        {{"option_id": "c1_o2", "value": "옵션2"}},
        {{"option_id": "c1_o3", "value": "옵션3"}}
      ],
      "selected": {{"option_id": "c1_o2", "value": "옵션2"}}
    }},
    {{
      "category_id": "c2",
      "category_name": "분류명2",
      "options": [
        {{"option_id": "c2_o1", "value": "옵션1"}},
        {{"option_id": "c2_o2", "value": "옵션2"}},
        {{"option_id": "c2_o3", "value": "옵션3"}},
        {{"option_id": "c2_o4", "value": "옵션4"}}
      ],
      "selected": {{"option_id": "c2_o3", "value": "옵션3"}}
    }},
    {{
      "category_id": "c3",
      "category_name": "분류명3",
      "options": [
        {{"option_id": "c3_o1", "value": "옵션1"}},
        {{"option_id": "c3_o2", "value": "옵션2"}},
        {{"option_id": "c3_o3", "value": "옵션3"}}
      ],
      "selected": {{"option_id": "c3_o1", "value": "옵션1"}}
    }},
    {{
      "category_id": "c4",
      "category_name": "분류명4",
      "options": [
        {{"option_id": "c4_o1", "value": "옵션1"}},
        {{"option_id": "c4_o2", "value": "옵션2"}},
        {{"option_id": "c4_o3", "value": "옵션3"}},
        {{"option_id": "c4_o4", "value": "옵션4"}},
        {{"option_id": "c4_o5", "value": "옵션5"}}
      ],
      "selected": {{"option_id": "c4_o2", "value": "옵션2"}}
    }},
    {{
      "category_id": "c5",
      "category_name": "분류명5",
      "options": [
        {{"option_id": "c5_o1", "value": "옵션1"}},
        {{"option_id": "c5_o2", "value": "옵션2"}},
        {{"option_id": "c5_o3", "value": "옵션3"}},
        {{"option_id": "c5_o4", "value": "옵션4"}}
      ],
      "selected": {{"option_id": "c5_o4", "value": "옵션4"}}
    }}
  ],
  "selected_context_summary": {{
    "분류명1": "선택된값1",
    "분류명2": "선택된값2",
    "분류명3": "선택된값3",
    "분류명4": "선택된값4",
    "분류명5": "선택된값5"
  }},
  "reselection_guide": "봇 수정 시 위 분류의 다른 옵션을 선택하면 다른 봇이 생성됩니다"
}}
```
<<<STEP1_END>>>

---

## 📋 2단계: 서비스 직원 봇 역할 20가지 나열 및 랜덤 선택

### 🎯 핵심 개념: 봇 = 실제 직원을 대신함

**상황:**
당신은 "{{category_title}}" 서비스를 운영하는 **방장(사업주)**입니다.
고객에게 서비스를 제공하기 위해 **직원을 채용**해야 합니다.
하지만 사람 대신 **봇(AI 직원)**을 고용하려고 합니다.

**봇의 정체:**
- 실제 매장/서비스 현장에 있는 **직원**
- 특정 **직무**를 수행하는 전문 인력
- 고객과 대화하며 **서비스를 제공**

**봇이 아닌 것:**
- 자동화 시스템 (자동 발급, 자동 추천)
- 검색 엔진 (정보 조회)
- 알림 도구 (푸시 알림)

---

### 📝 임무

**1단계 선택 조건**을 반영하여, 
해당 서비스 현장에서 일할 **직원 봇 역할 20가지**를 나열하세요.

각 봇은 **실제 존재하는 직업/직무**를 담당해야 합니다.

---

### 🎯 직업군 예시 (서비스별)

#### 여행/관광 서비스
**실제 직원들:**
- 여행 가이드 (투어 안내)
- 투어 코디네이터 (일정 조율)
- 현지 가이드 (지역 전문가)
- 여행사 직원 (예약 접수)
- 공항 안내원 (공항 서비스)
- 호텔 컨시어지 (숙박 서비스)
- 렌터카 상담원 (차량 대여)
- 액티비티 강사 (체험 지도)

#### 쇼핑/리테일 서비스
**실제 직원들:**
- 매장 판매원 (상품 판매)
- MD (상품 기획자)
- 스타일리스트 (코디 조언)
- 피팅 도우미 (사이즈 상담)
- 매장 점장 (고객 관리)
- 재고 관리자 (재입고 안내)
- VIP 담당자 (단골 고객 관리)
- 교환/환불 담당자 (AS 처리)

#### 식음료 서비스
**실제 직원들:**
- 주문 접수원 (주문 받기)
- 소믈리에 (와인 추천)
- 바리스타 (커피 추천)
- 영양사 (식단 조언)
- 셰프 (메뉴 설명)
- 홀 매니저 (테이블 관리)
- 배달 기사 (배달 조율)

#### 쿠폰/이벤트 서비스
**실제 직원들:**
- 프로모션 매니저 (이벤트 안내)
- 할인 상담원 (쿠폰 설명)
- 멤버십 담당자 (포인트 관리)
- 이벤트 기획자 (참여 유도)
- 고객 응대원 (문의 응답)
- 혜택 안내원 (할인 정보 제공)

#### 육아 서비스
**실제 직원들:**
- 육아 도우미 (돌봄 조언)
- 보육교사 (발달 상담)
- 소아과 간호사 (건강 조언)
- 영양사 (이유식 상담)
- 놀이 선생님 (놀이 지도)
- 육아 용품 판매원 (제품 추천)

---

### 📋 출력 형식

각 봇은 다음 정보를 포함:
```json
{{
  "feature_id": "f001",
  "name": "{{직업명}} ({{담당 업무}})",
  "job_title": "{{실제 직업명}}",
  "description": "{{이 직원이 고객에게 제공하는 서비스}}",
  "user_value": "{{고객이 얻는 가치}}",
  "work_scenario": "{{실제 업무 시나리오}}",
  "complexity": "low|medium|high",
  "estimated_api_calls": 2
}}
```

---

### 🚨 필수 규칙

#### ✅ 반드시 포함

**1. 실제 존재하는 직업명**
- "여행 가이드", "매장 판매원", "소믈리에", "호텔 컨시어지"
- ❌ "최적화 전문가", "컨설턴트", "코치" 같은 추상적 이름

**2. 구체적인 직무 설명**
- 이 직원이 **실제로 하는 일**
- 예: "고객의 체형을 보고 어울리는 옷 사이즈와 스타일을 추천"

**3. 대화형 서비스**
- 고객과 질문/답변하며 서비스 제공
- 예: "어떤 스타일 선호하세요?" → "그럼 이 옷이 잘 어울리겠네요"

**4. 1단계 조건 모두 반영**
- 5가지 선택 조건을 모든 직원에 적용

---

#### ❌ 절대 금지

**자동화 시스템:**
- ❌ "자동 발급", "자동 추천", "자동 매칭"

**검색/필터 도구:**
- ❌ "최적 검색", "조건별 필터링"

**알림 시스템:**
- ❌ "만료 알림", "푸시 알림"

**추상적 직업:**
- ❌ "전문가", "컨설턴트", "상담사", "코치"
- ✅ "판매원", "가이드", "매니저", "직원"

---

### 📝 구체적 예시

#### 예시 1: 쿠폰/이벤트 + 제주도 숙박

**❌ 나쁜 예시:**
```json
{{
  "name": "제주도 쿠폰 최적화 전문가",
  "job_title": "최적화 전문가",
  "why_bad": "실제 존재하는 직업 아님, 추상적"
}}
```

**✅ 좋은 예시 1:**
```json
{{
  "feature_id": "f001",
  "name": "제주도 숙박 프로모션 매니저",
  "job_title": "프로모션 매니저",
  "description": "호텔/펜션의 현재 진행 중인 이벤트와 할인 쿠폰을 고객 상황에 맞게 설명하고, 어떤 쿠폰을 언제 사용하면 가장 이득인지 안내합니다. 마치 호텔 프론트에서 고객에게 '지금 이 쿠폰 쓰시면 더 저렴해요'라고 알려주는 것처럼 동작합니다.",
  "user_value": "직원이 직접 알려주는 것처럼 숨은 할인 혜택 확보",
  "work_scenario": "고객: 3박 예약하고 싶어요 → 매니저: 지금 4박 하시면 1박 무료 이벤트 중이에요. 예산이 어떻게 되세요? → 맞춤 제안",
  "complexity": "medium",
  "estimated_api_calls": 3
}}
```

**✅ 좋은 예시 2:**
```json
{{
  "feature_id": "f002",
  "name": "제주도 현지 여행 가이드",
  "job_title": "현지 가이드",
  "description": "제주도에서 10년 일한 현지 가이드처럼, 고객의 여행 일정과 예산을 듣고 숙박지 근처의 숨은 맛집, 할인받을 수 있는 액티비티, 현지인만 아는 이벤트 정보를 알려줍니다.",
  "user_value": "현지 가이드 수준의 인사이트로 여행 만족도 2배 상승",
  "work_scenario": "고객: 서귀포 쪽 펜션 잡았어요 → 가이드: 그럼 차로 5분 거리에 해산물 직판장 있는데 거기 쿠폰 쓰면 30% 할인돼요",
  "complexity": "high",
  "estimated_api_calls": 4
}}
```

**✅ 좋은 예시 3:**
```json
{{
  "feature_id": "f003",
  "name": "숙박 시설 멤버십 담당자",
  "job_title": "멤버십 담당자",
  "description": "호텔 체인의 멤버십 담당 직원처럼, 고객의 포인트 현황을 보고 '이번에 포인트 쌓으실래요, 아니면 할인 받으실래요?', '다음 달에 또 오시면 무료 업그레이드 가능해요' 같은 맞춤 조언을 제공합니다.",
  "user_value": "포인트 전략으로 장기적으로 50만원 이상 절감",
  "work_scenario": "고객: 포인트가 5만점 있어요 → 담당자: 지금 쓰면 3만원 할인이고, 모으면 다음에 무료 숙박이에요. 언제 또 오세요?",
  "complexity": "medium",
  "estimated_api_calls": 3
}}
```

**✅ 좋은 예시 4:**
```json
{{
  "feature_id": "f004",
  "name": "여행사 패키지 상담 직원",
  "job_title": "여행사 직원",
  "description": "여행사 창구 직원처럼, 고객의 예산과 일정을 듣고 '숙박+렌터카+액티비티'를 묶은 패키지 상품을 제안하며, 개별 구매 vs 패키지 중 어느 쪽이 저렴한지 계산해서 보여줍니다.",
  "user_value": "여행사 직원 수준의 패키지 설계로 20% 비용 절감",
  "work_scenario": "고객: 100만원 예산이에요 → 직원: 패키지로 하면 85만원에 다 되는데, 렌터카는 따로 하시겠어요?",
  "complexity": "high",
  "estimated_api_calls": 5
}}
```

---

#### 예시 2: 쇼핑 + 의류

**✅ 좋은 예시:**
```json
{{
  "feature_id": "f001",
  "name": "매장 스타일리스트",
  "job_title": "스타일리스트",
  "description": "백화점 명품관 스타일리스트처럼, 고객의 체형, 피부톤, 선호 스타일을 듣고 어울리는 옷을 골라주고 코디를 제안합니다.",
  "work_scenario": "고객: 결혼식 갈 옷 찾아요 → 스타일리스트: 체형이 어떻게 되세요? 어떤 색 좋아하세요?",
  "complexity": "high",
  "estimated_api_calls": 4
}}
```
```json
{{
  "feature_id": "f002",
  "name": "매장 판매 사원",
  "job_title": "판매 사원",
  "description": "옷 가게 판매원처럼, 고객이 고른 옷의 사이즈가 맞는지 확인하고, 비슷한 스타일의 다른 상품도 함께 추천하며, 지금 할인 중인 제품을 알려줍니다.",
  "work_scenario": "고객: 이 청바지 있어요? → 판매원: 55사이즈 재고 있어요. 혹시 상의도 보실래요? 지금 세트로 사면 20% 할인이에요",
  "complexity": "medium",
  "estimated_api_calls": 3
}}
```

---

#### 예시 3: 육아 + 이유식

**✅ 좋은 예시:**
```json
{{
  "feature_id": "f001",
  "name": "소아 영양사",
  "job_title": "영양사",
  "description": "병원 소아과 영양사처럼, 아기 개월 수와 알레르기 여부를 듣고 적합한 이유식 재료와 조리법을 추천하며, 영양 균형을 맞추는 방법을 알려줍니다.",
  "work_scenario": "부모: 6개월 아기인데 뭐 먹여야 해요? → 영양사: 알레르기 있나요? 그럼 쌀미음부터 시작하세요",
  "complexity": "high",
  "estimated_api_calls": 4
}}
```
```json
{{
  "feature_id": "f002",
  "name": "육아 용품 판매 사원",
  "job_title": "판매 사원",
  "description": "육아 용품 매장 직원처럼, 부모의 필요(예: 외출용 유모차, 집에서 쓸 바운서)를 듣고 예산에 맞는 제품을 추천하며, 지금 할인 중인 상품을 안내합니다.",
  "work_scenario": "부모: 유모차 사려고요 → 판매원: 주로 어디서 쓰세요? 예산은요? 지금 이 모델 30% 할인 중이에요",
  "complexity": "medium",
  "estimated_api_calls": 3
}}
```

---

### 🎯 20개 직원 봇 생성 시 주의사항

**1. 다양한 직무 분산**
- 같은 직업 반복 X
- 예: 판매원 10개 (X) → 판매원, MD, 스타일리스트, 피팅 도우미, 점장 등 (O)

**2. 고객 접점 직원 우선**
- 고객과 직접 대화하는 직원
- 예: 판매원 (O), 재고 관리자 (△)

**3. 실제 현장 직무**
- 실제 매장/서비스 현장에 존재하는 직업
- 예: 스타일리스트 (O), AI 추천 엔진 (X)

---

### 📋 최종 출력 형식

<<<STEP2_START>>>
```json
{{
  "step": 2,
  "description": "선택된 조건에 맞는 서비스 직원 봇 역할 20가지",
  "category": "{{category_title}}",
  "based_on_context": {{
    "분류명1": "선택된값1",
    "분류명2": "선택된값2",
    "분류명3": "선택된값3",
    "분류명4": "선택된값4",
    "분류명5": "선택된값5"
  }},
  "employee_bots": [
    {{
      "feature_id": "f001",
      "name": "{{직업명}} ({{담당 업무}})",
      "job_title": "{{실제 직업명}}",
      "description": "{{이 직원이 고객에게 제공하는 서비스}}",
      "user_value": "{{고객이 얻는 가치}}",
      "work_scenario": "{{실제 업무 시나리오}}",
      "complexity": "medium",
      "estimated_api_calls": 3
    }}
    (f002 ~ f020까지 20개)
  ],
  "selected_feature": {{
    "feature_id": "f008",
    "name": "선택된 직원 봇 이름",
    "job_title": "선택된 직업명",
    "description": "설명",
    "user_value": "가치",
    "work_scenario": "시나리오",
    "complexity": "medium",
    "estimated_api_calls": 3
  }},
  "reselection_guide": "봇 수정 시 위 20개 직원 중 다른 것을 선택하면 완전히 다른 봇이 생성됩니다"
}}
```
<<<STEP2_END>>>
---





## 📋 3단계: 직원 업무 프로세스 설계 및 변수 분류 (3-Phase)

### 🎯 핵심 개념

**이 단계의 목적:**
"{{selected_function.name}}" 직원이 고객에게 서비스를 제공하는 **전체 업무 프로세스**를 설계하고,
각 단계에서 **어떤 정보가 필요한지** 파악한 후, **변수로 분류**합니다.

**사고 방식:**
당신이 실제로 이 직원이라고 상상하세요.
고객이 와서 서비스를 요청하면, **시작부터 완료까지 어떤 단계를 거치나요?**

---

### 📋 Phase 1: 업무 프로세스 설계 (직원 관점)

**질문: "{{selected_function.name}}" 직원이 고객에게 서비스를 제공하는 전체 과정은 무엇인가요?**

#### Step 1: 서비스 유형 파악

먼저 이 서비스가 어떤 유형인지 판단하세요:

**A. 예약/약속형 서비스**
- 예: 여행 가이드, 강사, 컨시어지, 상담원
- 특징: 시간, 장소, 일정 조율 필요
- 프로세스: 니즈 파악 → 일정 조율 → 장소 확정 → 조건 확인 → 예약 확정 → 서비스 제공

**B. 즉시 처리형 서비스**
- 예: 매장 판매원, 주문 접수원, 고객 응대원
- 특징: 즉시 상담/판매, 재고 확인, 결제
- 프로세스: 니즈 파악 → 상품 추천 → 재고 확인 → 시착/체험 → 결제 → 포장/배송

**C. 분석/검토형 서비스**
- 예: 상품 MD, 안전 점검관, 품질 관리자
- 특징: 데이터 분석, 조건 검토, 보고서 작성
- 프로세스: 대상 확인 → 항목 리스트 → 현장 조사 → 데이터 수집 → 분석 → 보고서 → 전달

**D. 배송/물류형 서비스**
- 예: 배달 기사, 배송 담당자
- 특징: 주소, 배송 시간, 배송 상태
- 프로세스: 주문 접수 → 상품 준비 → 배송지 확인 → 배송 → 수령 확인

**E. 지속 관리형 서비스**
- 예: 멤버십 담당자, 고객 관리자
- 특징: 장기 관계, 주기적 소통
- 프로세스: 고객 등록 → 니즈 분석 → 혜택 제공 → 주기적 소통 → 만족도 관리

---

#### Step 2: 업무 프로세스 단계별 분해

**프로세스 설계 원칙:**

모든 서비스는 **3단계 구조**를 따릅니다:

**A단계: 기본 정보 수집**
- 사용자 입력: 날짜, 인원, 예산 등
- 목적: 무엇을 원하는지 파악

**B단계: 옵션 조회 및 선택** (← **매우 중요!**)
- 정보 조회용 API 호출 (서브봇)
- 옵션을 사용자에게 제시
- **사용자가 선택** (사용자 입력!)
- 필요시 추가 정보 수집

**C단계: 최종 실행**
- 모든 정보가 모였음
- **최종 Webhook 호출**
- 서비스 완료!

---

**중요한 차이:**

❌ **잘못된 프로세스:**
```
A. 정보 수집 → B. API 호출 → 끝
```

✅ **올바른 프로세스:**
```
A. 정보 수집 → B. 조회 API → 사용자 선택 → C. 최종 Webhook
```

---

**구체적 예시:**

**예시 1: 예약/약속형 - 리조트 컨시어지**
```
step1: 고객 니즈 파악 (A단계)
  - action: 체크인/체크아웃 날짜, 인원 확인
  - purpose: 기본 조건 파악
  - required_info: [check_in_date, check_out_date, number_of_guests]

step2: 객실 타입 선호 확인 (A단계)
  - action: 어떤 타입의 객실을 선호하는지 질문
  - purpose: 고객 취향 파악
  - required_info: [room_type_preference, budget]

step3: 가용 객실 조회 (B단계 - 조회)
  - action: 조건에 맞는 가용 객실을 API로 조회
  - purpose: 실제 예약 가능한 방 확인
  - required_info: [available_rooms] ← 서브봇이 API 호출

step4: 객실 옵션 제시 및 선택 (B단계 - 선택) ← **핵심!**
  - action: 조회된 객실들을 고객에게 보여주고 선택 유도
  - purpose: 고객이 원하는 방 확정
  - required_info: [selected_room_id] ← **사용자 입력!**
  - 예: "101호 스위트(15만원)와 203호 델럭스(10만원)가 있어요. 어느 방 원하세요?"

step5: 추가 정보 수집 (B단계)
  - action: 결제 방법, 특별 요청사항 확인
  - purpose: 예약 완료에 필요한 세부 정보
  - required_info: [payment_method, special_requests]

step6: 고객 정보 확인 (B단계)
  - action: 예약자 이름, 연락처 확인
  - purpose: 예약 확정 및 연락
  - required_info: [customer_name, customer_phone]

step7: 예약 확정 (C단계) ← **최종 Webhook**
  - action: 모든 정보를 최종 Webhook으로 전송
  - purpose: 실제 예약 완료
  - webhook_call: POST /api/{{api_id}}
  - 결과: reservation_id 발급

step8: 체크인 안내 (C단계 후)
  - action: 체크인 시간, 위치 안내
  - purpose: 고객 편의
```

**예시 2: 즉시 처리형 - 의류 매장 판매원**
```
step1: 고객 니즈 파악 (A단계)
  - action: 어떤 옷을 찾는지 질문
  - purpose: 고객 취향 파악
  - required_info: [product_type, purpose, budget]

step2: 고객 정보 수집 (A단계)
  - action: 체형, 선호 색상, 스타일 확인
  - purpose: 맞춤 추천
  - required_info: [body_type, preferred_color, preferred_style]

step3: 재고 조회 (B단계 - 조회)
  - action: 조건에 맞는 상품 재고 API 호출
  - purpose: 구매 가능 상품 확인
  - required_info: [available_products] ← 서브봇이 API 호출

step4: 상품 제시 및 선택 (B단계 - 선택) ← **핵심!**
  - action: 재고 있는 상품들을 보여주고 선택 유도
  - purpose: 고객이 원하는 상품 확정
  - required_info: [selected_product_id] ← **사용자 입력!**
  - 예: "이 셔츠(5만원)와 저 재킷(8만원)이 있어요. 어떤 걸 원하세요?"

step5: 사이즈 선택 (B단계)
  - action: 사이즈 확인 및 선택
  - purpose: 맞는 사이즈 확정
  - required_info: [selected_size]

step6: 시착 지원 (B단계)
  - action: 피팅룸 안내 및 확인
  - purpose: 구매 전 최종 확인
  - required_info: [fitting_result]

step7: 추가 상품 제안 (B단계)
  - action: 코디 가능한 다른 상품 추천
  - purpose: 추가 판매
  - required_info: [additional_items]

step8: 결제 진행 (C단계) ← **최종 Webhook**
  - action: 결제 방법 확인 및 최종 Webhook 호출
  - purpose: 구매 완료
  - webhook_call: POST /api/{{api_id}}
  - 결과: order_id 발급

step9: 포장 및 안내
  - action: 상품 포장, 교환/환불 정책 안내
  - purpose: 구매 완료
```

**예시 3: 분석/검토형 - 안전 점검관**
```
step1: 점검 대상 확인 (A단계)
  - action: 어떤 시설을 점검하는지 확인
  - purpose: 점검 범위 파악
  - required_info: [facility_name, facility_address, facility_type]

step2: 점검 항목 조회 (B단계 - 조회)
  - action: 시설 유형에 맞는 점검 항목 API 조회
  - purpose: 점검 체크리스트 확보
  - required_info: [inspection_checklist] ← 서브봇이 API 호출

step3: 점검 일정 조율 (A단계)
  - action: 현장 방문 가능 날짜/시간 확인
  - purpose: 점검 스케줄 확정
  - required_info: [inspection_date, inspection_time]

step4: 현장 접근 정보 (A단계)
  - action: 담당자 연락처, 접근 방법 확인
  - purpose: 원활한 현장 조사
  - required_info: [contact_person, contact_phone, access_method]

step5: 현장 점검 수행 (서비스 실행 - 오프라인)
  - action: 실제 시설 점검
  - purpose: 데이터 수집
  - required_info: [measurement_data, photos, risk_factors]

step6: 점검 항목별 결과 입력 (B단계)
  - action: 각 항목의 합격/불합격 입력
  - purpose: 점검 결과 기록
  - required_info: [inspection_results]

step7: 종합 위험도 평가 (B단계)
  - action: 전체 점검 결과를 바탕으로 등급 판정
  - purpose: 안전 등급 결정
  - required_info: [overall_grade, critical_issues]

step8: 보고서 제출 (C단계) ← **최종 Webhook**
  - action: 모든 점검 결과를 최종 Webhook으로 전송
  - purpose: 공식 보고서 생성
  - webhook_call: POST /api/{{api_id}}
  - 결과: report_id 발급

step9: 결과 전달 및 후속 조치
  - action: 담당자에게 보고서 전달, 재점검 일정 안내
  - purpose: 개선 조치 유도
```

**예시 4: 배송/물류형 - 온라인 쇼핑몰 배송 담당자**
```
step1: 주문 정보 확인 (A단계)
  - action: 주문 번호로 주문 내역 조회
  - purpose: 배송할 상품 확인
  - required_info: [order_id, product_list]

step2: 배송지 정보 수집 (A단계)
  - action: 배송 주소, 수령인 정보 확인
  - purpose: 정확한 배송
  - required_info: [delivery_address, recipient_name, recipient_phone]

step3: 배송 가능 일시 조회 (B단계 - 조회)
  - action: 배송 가능한 날짜/시간대 API 조회
  - purpose: 배송 스케줄 확인
  - required_info: [available_delivery_slots] ← 서브봇이 API 호출

step4: 배송 일시 선택 (B단계 - 선택) ← **핵심!**
  - action: 가능한 배송 시간대를 보여주고 선택 유도
  - purpose: 고객 편의에 맞는 배송
  - required_info: [selected_delivery_date, selected_delivery_time] ← **사용자 입력!**
  - 예: "내일 오전, 내일 오후, 모레 오전 중 언제가 좋으세요?"

step5: 특별 요청 확인 (B단계)
  - action: 배송 시 주의사항, 문 앞 배송 여부 등 확인
  - purpose: 맞춤 배송
  - required_info: [delivery_note, leave_at_door]

step6: 배송 신청 (C단계) ← **최종 Webhook**
  - action: 모든 배송 정보를 최종 Webhook으로 전송
  - purpose: 배송 시작
  - webhook_call: POST /api/{{api_id}}
  - 결과: delivery_id, tracking_number 발급

step7: 배송 진행
  - action: 실제 배송 수행
  - purpose: 상품 전달

step8: 수령 확인
  - action: 고객 수령 확인
  - purpose: 배송 완료
```

---

#### Step 3: 각 단계별 필요 정보 추출

**정보 추출 프로세스:**

1. **workflow의 각 step 검토**
   - 모든 step의 required_info를 수집

2. **중복 제거**
   - 여러 step에서 중복되는 정보는 하나로 통합

3. **구체화**
   - 모호한 정보는 세분화
   - 예: "시간" → "시작 시간", "종료 시간"

4. **선택 변수 추가** ← **매우 중요!**
   - 조회 API 결과가 **목록/배열**이면
   - 반드시 **선택 변수**가 필요!
   - 예: available_rooms → selected_room_id
   - 예: available_products → selected_product_id
   - 예: available_dates → selected_date

5. **최종 리스트 작성**
   - total_info_needed로 정리

---

**정보 카테고리 예시 (참고용, 해당되는 것만 선택):**

**예시 A: 고객 식별 정보**
- 예: 이름, 연락처, 이메일, 회원번호, 나이, 성별

**예시 B: 서비스/상품 정보**
- 예: 상품명, 서비스 종류, 옵션, 수량, 규모, 난이도, 레벨

**예시 C: 시간 관련 정보** (시간이 중요한 서비스)
- 예: 희망 날짜, 시작 시간, 종료 시간, 소요 시간, 요일

**예시 D: 장소 관련 정보** (장소가 중요한 서비스)
- 예: 주소, GPS 좌표, 지역, 만남 장소, 배송 주소

**예시 E: 인원 관련 정보** (그룹 서비스)
- 예: 참여 인원, 연령대, 단독/그룹 여부

**예시 F: 준비물/조건** (특수 요구사항)
- 예: 필요 장비, 사전 준비물, 제한 사항, 알레르기, 특이사항

**예시 G: 비용 관련 정보**
- 예: 가격, 할인율, 쿠폰 코드, 결제 방법, 선결제/후불

**예시 H: 확인/동의 사항**
- 예: 약관 동의, 취소 정책 확인, 개인정보 수집 동의, 환불 정책

**예시 I: 배송/물류 정보** (배송 서비스)
- 예: 배송 주소, 수령인, 희망 배송일, 배송 메모

**예시 J: 분석/검토 정보** (분석 서비스)
- 예: 점검 대상, 점검 항목, 측정값, 위험도

**예시 K: 조회 결과 및 선택** ← **매우 중요!**
- 조회 결과: available_rooms, available_products, available_dates
- **선택 결과: selected_room_id, selected_product_id, selected_date**

**예시 L: 피드백/평가 정보**
- 예: 만족도, 리뷰, 개선 요청사항

---

**중요:**
- 위 예시는 **참고용**입니다
- 해당 서비스에 **실제로 필요한 정보만** 선택하세요
- 예시에 없는 정보도 **자유롭게 추가**하세요

---


### 📋 Phase 1 출력

<<<BUSINESS_PLAN_START>>>
```json
{{
  "employee_role": "{{selected_function.name}}",
  "job_title": "{{selected_function.job_title}}",
  "service_type": "예약/약속형|즉시처리형|분석/검토형|배송/물류형|지속관리형",
  "final_goal": "이 서비스의 최종 목적 (예: 객실 예약 확정, 상품 구매 완료, 보고서 제출)",
  
  "service_workflow": {{
    "step1": {{
      "action": "구체적 행동",
      "purpose": "왜 필요한가",
      "stage": "A|B|C",
      "required_info": ["정보1", "정보2"]
    }},
    "step2": {{
      "action": "구체적 행동",
      "purpose": "왜 필요한가",
      "stage": "A|B|C",
      "required_info": ["정보1", "정보2"]
    }}
    ... (서비스 특성에 맞게 5-10단계, 반드시 B단계에 선택 과정 포함)
  }},
  
  "total_info_needed": [
    "고객 기본 정보들 (A단계)",
    "조회 API 결과 (B단계)",
    "사용자 선택 결과 (B단계) ← 매우 중요!",
    "추가 세부 정보 (B단계)",
    ... (최소 8개 이상)
  ]
}}
```
<<<BUSINESS_PLAN_END>>>

---





### 📋 Phase 2: 최종 Webhook 요청 데이터 설계

**API Endpoint:**
- 고유 API ID: `{api_id}`
- 전체 경로: `/api/{api_id}`

**중요: 이것은 서비스를 실제로 실행하는 최종 Webhook입니다**

이 Webhook은:
- 서비스의 **최종 목적**을 달성합니다 (예: 예약 확정, 구매 완료, 보고서 제출)
- 모든 정보가 **완전히 수집된 후** 호출됩니다 (C단계)
- 중간 조회용 API가 **아닙니다**

예시:
- 예약 확정 Webhook (GET 아님, POST!)
- 구매 완료 Webhook
- 보고서 제출 Webhook
- 배송 신청 Webhook

**이 Webhook에 보낼 데이터:**
- 사용자 입력 (A단계)
- **사용자 선택 결과 (B단계) ← 매우 중요!**
- 필요시 조회 API 결과 일부 (B단계)

**Phase 1의 `total_info_needed`를 기반으로 최종 Webhook 요청 Body를 설계합니다.**

**설계 원칙:**
- 각 정보를 적절한 필드명으로 변환 (영문, snake_case)
- 데이터 타입 지정 (String, Number, Boolean, Date, Time, Array, Object)
- 예시 값 제공

**예시:**
```json
POST /api/{api_id}
{{
  "check_in_date": "2025-07-10",
  "check_out_date": "2025-07-13",
  "number_of_guests": 3,
  "selected_room_id": "101",  ← 선택 결과!
  "payment_method": "card",
  "customer_name": "홍길동",
  "customer_phone": "010-1234-5678"
}}
```

---

📋 Phase 3: 변수 분류 및 서브봇 설계
🎯 핵심 개념
Phase 2의 각 필드를 분류하고, 서브봇의 동작 방식을 명확히 정의합니다.
분류 기준:
질문 1: 사용자에게 물어볼 수 있나?

YES → 사용자 입력 변수
NO → 질문 2

질문 2: 외부 정보를 조회해야 하나?

YES → 서브봇 변수 (2가지 타입)


🤖 서브봇 2가지 타입
타입 A: 즉시 복귀형 (direct_return)
특징:

API 호출 → 결과 저장 → 즉시 메인봇 복귀
사용자 입력 필요 없음
메인봇이 바로 다음 단계 진행

예시:

쿠폰 상세 조회
할인 금액 계산
날씨 정보 조회
회원 포인트 확인

흐름:
메인봇 → 서브봇 호출 
       → API 호출
       → 결과 저장
       → 메인봇 복귀 (결과 전달)
       → 메인봇 다음 단계

타입 B: 선택 대기형 (selection_required)
특징:

API 호출 → 결과 제시 → 사용자 선택 대기 → 선택 결과와 함께 메인봇 복귀
사용자 입력 필요 (선택)
선택이 완료되어야 메인봇 복귀

예시:

쿠폰 목록 조회 + 선택
상품 재고 조회 + 선택
가능한 예약 시간 조회 + 선택
배송 가능 일시 조회 + 선택

흐름:
메인봇 → 서브봇 호출
       → API 호출 (목록 조회)
       → 결과 제시
       → 사용자 선택 대기 ← 서브봇이 대기!
       → 선택 완료
       → 메인봇 복귀 (목록 + 선택 결과 전달)
       → 메인봇 다음 단계

       


       
🔄 변수 실행 순서
중요: 변수는 workflow의 step 순서를 따릅니다. 일반 변수와 서브봇 변수가 섞여 있어도 됩니다.
예시 1: 일반 → 서브봇 → 일반
step1: customer_name (일반)
step2: budget (일반)
step3: available_coupons (서브봇 - 선택형)
step4: payment_method (일반) ← 선택된 쿠폰 기반으로 질문
step5: coupon_details (서브봇 - 즉시형)
예시 2: 서브봇 → 일반 → 서브봇
step1: available_rooms (서브봇 - 선택형)
step2: special_requests (일반) ← 선택된 방 기반으로 질문
step3: room_details (서브봇 - 즉시형)
핵심:

서브봇 선택 결과를 바탕으로 다음 일반 질문 가능
순서는 workflow step을 따름
일반/서브봇 섞여도 OK


📋 변수 분류 작성 가이드
A. 사용자 입력 변수
작성 원칙:

사용자에게 직접 물어봐서 받는 모든 정보
단, 조회 결과에서 선택하는 것은 제외 (서브봇이 처리)

필수 포함 내용:
json{{
  "variable_id": "v001",
  "variable_name": "필드명",
  "question": "사용자에게 물어볼 질문",
  "data_type": "String|Number|Boolean|Date",
  "is_mandatory": true|false,
  "validation_rule": "검증 규칙",
  
  "llm_execution_guide": {{
    "when_to_execute": "언제 실행하는가",
    "prerequisite": "선행 조건 (먼저 수집되어야 할 변수)",
    "how_to_ask": "어떻게 질문하는가 (구체적인 예시 포함)",
    "user_friendly_tone": "대화 톤 가이드",
    
    "validation": {{
      "rule": "검증 규칙 상세",
      "on_invalid": "검증 실패 시 메시지",
      "auto_format": "자동 변환 규칙 (있으면)",
      "example_valid": ["유효한 예시1", "예시2"],
      "example_invalid": ["무효한 예시1", "예시2"]
    }},
    
    "after_collection": "수집 후 다음 행동"
  }}
}}
예시 1: 이름
json{{
  "variable_id": "v001",
  "variable_name": "customer_name",
  "question": "고객님 성함을 알려주세요",
  "data_type": "String",
  "is_mandatory": true,
  "validation_rule": "최소 2자 이상의 한글 또는 영문",
  
  "llm_execution_guide": {{
    "when_to_execute": "대화 시작 시 가장 먼저 실행",
    "prerequisite": "없음",
    "how_to_ask": "친근하고 정중하게 성함을 물어보세요. '안녕하세요! 제주도 숙박 예약을 도와드릴게요. 먼저 성함을 알려주시겠어요?'",
    "user_friendly_tone": "격식을 차리되 친근한 톤으로, 예약 서비스임을 명시하세요",
    
    "validation": {{
      "rule": "최소 2자 이상의 한글 또는 영문",
      "on_invalid": "'성함은 2글자 이상 입력해주세요. 예: 홍길동' 라고 정중하게 요청하세요",
      "example_valid": ["홍길동", "김철수", "John Smith", "이나영"],
      "example_invalid": ["홍", "a", "123", "!@#"]
    }},
    
    "after_collection": "customer_name 필드에 저장 후, '감사합니다 {{이름}}님! 예약을 도와드리겠습니다'라고 인사하고 즉시 다음 변수(customer_phone) 수집으로 넘어가세요"
  }}
}}
예시 2: 전화번호
json{{
  "variable_id": "v002",
  "variable_name": "customer_phone",
  "question": "연락 가능한 전화번호를 입력해주세요",
  "data_type": "String",
  "is_mandatory": true,
  "validation_rule": "010-XXXX-XXXX 형식",
  
  "llm_execution_guide": {{
    "when_to_execute": "customer_name 수집 직후",
    "prerequisite": "customer_name이 반드시 먼저 수집되어야 함",
    "how_to_ask": "예약 확인을 위해 연락처가 필요하다고 설명하세요. '예약 확인을 위해 연락 가능한 전화번호를 알려주시겠어요?'",
    "user_friendly_tone": "개인정보 수집 목적을 명확히 설명하세요",
    
    "validation": {{
      "rule": "010-XXXX-XXXX 형식 (하이픈 포함 또는 제외 모두 허용)",
      "on_invalid": "'010-1234-5678' 형식으로 입력해주세요' 라고 안내하세요",
      "auto_format": "사용자가 '01012345678'처럼 입력하면 자동으로 '010-1234-5678'로 변환하여 저장하세요",
      "example_valid": ["010-1234-5678", "01012345678", "010-9999-8888"],
      "example_invalid": ["12345678", "02-1234-5678", "1234"]
    }},
    
    "privacy_assurance": "전화번호는 예약 확인 및 연락 용도로만 사용된다고 반드시 안내하세요",
    "after_collection": "customer_phone 필드에 저장 후 즉시 다음 변수(travel_start_date) 수집으로 넘어가세요"
  }}
}}
예시 3: 날짜
json{{
  "variable_id": "v003",
  "variable_name": "travel_start_date",
  "question": "제주도 여행 시작 날짜를 선택해주세요 (YYYY-MM-DD)",
  "data_type": "Date",
  "is_mandatory": true,
  "validation_rule": "오늘 이후 날짜",
  
  "llm_execution_guide": {{
    "when_to_execute": "customer_phone 수집 직후",
    "prerequisite": "customer_phone이 반드시 먼저 수집되어야 함",
    "how_to_ask": "여행 일정을 물어보세요. '제주도 여행은 언제 시작하시나요? 예를 들어 2025-08-01처럼 알려주세요'",
    "user_friendly_tone": "형식 예시를 반드시 함께 제시하세요",
    
    "validation": {{
      "rule": "YYYY-MM-DD 형식이며, 오늘 날짜보다 미래여야 함",
      "on_invalid_format": "'2025-08-01'처럼 년-월-일 형식으로 입력해주세요' 라고 안내하세요",
      "on_past_date": "이미 지난 날짜입니다. 앞으로의 여행 날짜를 입력해주세요",
      "flexible_parsing": "사용자가 '다음 주 월요일', '8월 1일' 같이 말하면 날짜로 변환하되 반드시 확인받으세요",
      "example_valid": ["2025-08-01", "2025-12-25", "2026-01-15"],
      "example_invalid": ["2024-01-01 (과거)", "08-01 (년도 없음)", "내일 (모호함)"]
    }},
    
    "after_collection": "travel_start_date 필드에 저장 후 즉시 다음 변수(travel_end_date) 수집으로 넘어가세요"
  }}
}}
예시 4: 예산
json{{
  "variable_id": "v005",
  "variable_name": "budget",
  "question": "예산 금액을 입력해주세요 (원 단위)",
  "data_type": "Number",
  "is_mandatory": true,
  "validation_rule": "0보다 큰 정수",
  
  "llm_execution_guide": {{
    "when_to_execute": "travel_end_date 수집 직후",
    "prerequisite": "travel_end_date가 반드시 먼저 수집되어야 함",
    "how_to_ask": "숙박 예산을 물어보되 쿠폰 추천에 필요하다고 설명하세요. '숙박 예산은 어느 정도이신가요? 최적의 쿠폰을 찾아드리겠습니다. (예: 70000)'",
    "explain_purpose": "왜 예산을 묻는지 반드시 설명하세요",
    
    "validation": {{
      "rule": "0보다 큰 정수 (원 단위)",
      "on_invalid": "숫자로 입력해주세요. 예: 70000",
      "auto_format": "'7만원', '70,000원' → 70000으로 변환하여 저장하세요",
      "range_guidance": "일반적으로 1만원 ~ 100만원 사이입니다. 너무 낮거나 높으면 재확인하세요",
      "example_valid": ["70000", "150000", "7만원 → 70000", "50,000 → 50000"],
      "example_invalid": ["abc", "-1000", "0", "천원"]
    }},
    
    "after_collection": "budget 필드에 저장 후, '예산 {{금액}}원 확인했습니다. 최적의 쿠폰을 찾아보겠습니다!'라고 말하고 즉시 다음 변수 수집으로 넘어가세요"
  }}
}}
예시 5: 선택 결과 기반 질문
json{{
  "variable_id": "v010",
  "variable_name": "payment_method",
  "question": "결제 방법을 선택해주세요",
  "data_type": "String",
  "is_mandatory": true,
  "validation_rule": "카드/계좌이체/간편결제 중 선택",
  
  "llm_execution_guide": {{
    "when_to_execute": "available_coupons 서브봇 완료 직후",
    "prerequisite": "selected_coupon_id가 반드시 먼저 수집되어야 함 (서브봇에서 선택됨)",
    "how_to_ask": "선택하신 쿠폰을 언급하며 결제 방법을 물어보세요. ''{{선택된 쿠폰명}}' 쿠폰으로 예약하시겠습니다. 어떤 방법으로 결제하시겠어요?'",
    "context_awareness": "이전 서브봇에서 선택한 쿠폰 정보를 활용하세요",
    
    "validation": {{
      "rule": "카드, 계좌이체, 간편결제 중 하나",
      "flexible_matching": "'카드', '신용카드', '체크카드' → 카드로 통일",
      "on_invalid": "카드, 계좌이체, 간편결제 중에서 선택해주세요",
      "example_valid": ["카드", "계좌이체", "간편결제", "신용카드 → 카드"],
      "example_invalid": ["현금", "포인트", "쿠폰"]
    }},
    
    "after_collection": "payment_method 필드에 저장 후 다음 변수로 넘어가세요"
  }}
}}

B. 서브봇 변수
서브봇은 workflow step 순서대로 일반 변수 사이에 위치할 수 있습니다.
B-1. 즉시 복귀형 서브봇 (direct_return)
필수 포함 내용:
json{{
  "variable_id": "v00X",
  "variable_name": "필드명",
  "sub_bot_id": "서브봇_id_task",
  "sub_bot_name": "서브봇 이름",
  "api_endpoint": "/api/{{api_id}}_서브봇_id_task",
  "purpose": "목적",
  "trigger_keyword": ["키워드1", "키워드2"],
  "source": "데이터 출처",
  "why_not_ask_user": "사용자에게 물으면 안 되는 이유",
  
  "execution_logic": {{
    "step1": "API 호출",
    "step2": "결과 저장",
    "step3": "완료"
  }},
  
  "subbot_type": "direct_return",
  "requires_user_selection": false,
  
  "llm_execution_guide": {{
    "when_to_execute": "언제 실행하는가",
    "prerequisite": ["선행 변수들"],
    "before_execution": "실행 전 사용자 안내 메시지",
    
    "api_call_detail": {{
      "method": "GET|POST",
      "url": "API URL with {{parameters}}",
      "body": {{}},  // POST인 경우만
      "parameters_from_collected": ["변수1", "변수2"],
      "parameter_mapping": {{
        "변수1": "설명"
      }},
      "example_call": "실제 호출 예시",
      "expected_response": {{
        "format": "예상 응답 형식",
        "required_fields": ["필수 필드들"],
        "extract_field": "추출할 필드 (있으면)"
      }}
    }},
    
    "on_success": {{
      "action": "성공 시 처리 방법",
      "display": "사용자에게 보여줄지 여부",
      "reason": "설명 (있으면)"
    }},
    
    "on_error": {{
      "message": "오류 시 메시지"
    }},
    
    "return_to_main": {{
      "when": "언제 복귀하는가",
      "return_data": {{
        "변수명": "설명"
      }},
      "next_action": "복귀 후 다음 행동"
    }}
  }}
}}
예시: 쿠폰 상세 조회
json{{
  "variable_id": "v007",
  "variable_name": "coupon_details",
  "sub_bot_id": "coupon_detail_task",
  "sub_bot_name": "쿠폰 상세 조회",
  "api_endpoint": "/api/{{api_id}}_coupon_detail_task",
  "purpose": "선택된 쿠폰의 상세 조건 조회",
  "trigger_keyword": ["쿠폰 상세", "조건"],
  "source": "CouponServiceAPI",
  "why_not_ask_user": "쿠폰 조건은 동적으로 변할 수 있어 자동 조회가 필요",
  
  "execution_logic": {{
    "step1": "API 호출: GET /api/coupons/{{selected_coupon_id}}",
    "step2": "결과를 coupon_details에 저장",
    "step3": "completed = true"
  }},
  
  "subbot_type": "direct_return",
  "requires_user_selection": false,
  
  "llm_execution_guide": {{
    "when_to_execute": "selected_coupon_id 수집 직후 즉시 실행",
    "prerequisite": ["selected_coupon_id"],
    "before_execution": "사용자에게 '쿠폰 상세 정보를 확인하고 있습니다...'라고 안내하세요",
    
    "api_call_detail": {{
      "method": "GET",
      "url": "/api/coupons/{{selected_coupon_id}}",
      "parameters_from_collected": ["selected_coupon_id"],
      "parameter_mapping": {{
        "selected_coupon_id": "이전 서브봇에서 사용자가 선택한 쿠폰 ID를 여기에 대입하세요"
      }},
      "example_call": "GET /api/coupons/CUP123",
      "expected_response": {{
        "format": "{{coupon_id: 'CUP123', title: '제주도 숙박 10% 할인', applicable_to: '숙박', valid_until: '2025-08-31', terms: '...', description: '...'}}",
        "required_fields": ["coupon_id", "title", "applicable_to", "valid_until"]
      }}
    }},
    
    "on_success": {{
      "action": "API 응답을 coupon_details 변수에 저장하세요",
      "display": "즉시 사용자에게 출력하세요",
      "format": "📋 쿠폰 상세 정보\n\n• 쿠폰명: {{title}}\n• 적용 대상: {{applicable_to}}\n• 유효기간: {{valid_until}}\n• 약관: {{terms}}"
    }},
    
    "on_error": {{
      "message": "쿠폰 정보를 불러오지 못했습니다. 다른 쿠폰을 선택하시겠어요?"
    }},
    
    "return_to_main": {{
      "when": "API 호출 완료 직후",
      "return_data": {{
        "coupon_details": "조회된 쿠폰 상세 정보 객체"
      }},
      "next_action": "메인봇으로 즉시 복귀하여 다음 변수 수집으로 진행"
    }}
  }}
}}

B-2. 선택 대기형 서브봇 (selection_required)
필수 포함 내용:
json{{
  "variable_id": "v00X",
  "variable_name": "필드명",
  "sub_bot_id": "서브봇_id_task",
  "sub_bot_name": "서브봇 이름",
  "api_endpoint": "/api/{{api_id}}_서브봇_id_task",
  "purpose": "목적",
  "trigger_keyword": ["키워드1", "키워드2"],
  "source": "데이터 출처",
  "why_not_ask_user": "사용자에게 물으면 안 되는 이유",
  
  "execution_logic": {{
    "step1": "API 호출",
    "step2": "결과 저장",
    "step3": "옵션 제시",
    "step4": "사용자 선택 대기",
    "step5": "선택 저장"
  }},
  
  "subbot_type": "selection_required",
  "requires_user_selection": true,
  
  "selection_config": {{
    "selection_variable": "selected_XXX_id",
    "selection_data_type": "String",
    "selection_prompt": "선택 유도 메시지",
    "selection_validation": {{
      "rule": "검증 규칙",
      "flexible_matching": {{
        "by_number": "숫자 매칭",
        "by_name": "이름 매칭",
        "by_id": "ID 매칭"
      }},
      "on_invalid": "무효 시 메시지",
      "example_valid": ["예시들"],
      "example_invalid": ["무효 예시들"]
    }}
  }},
  
  "llm_execution_guide": {{
    "when_to_execute": "언제 실행하는가",
    "prerequisite": ["선행 변수들"],
    "before_execution": "실행 전 안내",
    
    "api_call_detail": {{
      "method": "GET",
      "url": "API URL",
      "parameters_from_collected": ["변수들"],
      "example_call": "예시",
      "expected_response": {{
        "format": "응답 형식"
      }}
    }},
    
    "on_success": {{
      "action": "성공 시 처리",
      "display_format": "출력 형식",
      "then": "다음 행동"
    }},
    
    "on_empty": {{
      "message": "결과 없을 때",
      "allow_change": "변경 옵션"
    }},
    
    "on_error": {{
      "message": "오류 메시지"
    }},
    
    "selection_handling": {{
      "wait_for_user": true,
      "on_valid_selection": {{
        "action": "유효 선택 시",
        "message": "확인 메시지"
      }},
      "on_invalid_selection": {{
        "message": "무효 선택 시"
      }}
    }},
    
    "return_to_main": {{
      "when": "선택 완료 후",
      "return_data": {{
        "목록_변수": "설명",
        "선택_변수": "설명"
      }},
      "next_action": "다음 행동"
    }}
  }}
}}
예시: 쿠폰 목록 조회 + 선택
json{{
  "variable_id": "v006",
  "variable_name": "available_coupons",
  "sub_bot_id": "coupon_query_task",
  "sub_bot_name": "쿠폰 목록 조회 및 선택",
  "api_endpoint": "/api/{{api_id}}_coupon_query_task",
  "purpose": "제주도 할인 쿠폰 목록을 조회하고 사용자가 선택하도록 함",
  "trigger_keyword": ["쿠폰 리스트", "할인 쿠폰", "쿠폰 조회"],
  "source": "CouponServiceAPI",
  "why_not_ask_user": "사용자가 쿠폰 목록을 직접 입력하면 오차가 발생하고 불편하며, 실시간 재고 확인 불가",
  
  "execution_logic": {{
    "step1": "API 호출: GET /api/coupons?region=jeju&start_date={{travel_start_date}}&budget={{budget}}",
    "step2": "결과를 available_coupons에 저장",
    "step3": "사용자에게 쿠폰 옵션 보기 좋게 제시",
    "step4": "사용자 선택 대기 (selected_coupon_id)",
    "step5": "선택이 유효하면 selected_coupon_id에 저장하고 completed = true"
  }},
  
  "subbot_type": "selection_required",
  "requires_user_selection": true,
  
  "selection_config": {{
    "selection_variable": "selected_coupon_id",
    "selection_data_type": "String",
    "selection_prompt": "어떤 쿠폰을 사용하시겠어요? 번호나 쿠폰 이름을 말씀해주세요",
    "selection_validation": {{
      "rule": "available_coupons 배열에 존재하는 coupon_id여야 함",
      "flexible_matching": {{
        "by_number": "사용자가 '1번', '첫번째', '1' 입력 시 → available_coupons[0].coupon_id 선택",
        "by_name": "사용자가 '숙박 쿠폰', '숙박' 입력 시 → title에 '숙박' 포함된 항목의 coupon_id 선택",
        "by_id": "사용자가 'CUP123' 입력 시 → 그대로 CUP123 사용"
      }},
      "on_invalid": "선택하신 쿠폰을 찾을 수 없습니다. 위 목록에서 번호나 이름으로 다시 선택해주세요",
      "example_valid": ["CUP123", "1번", "첫번째", "숙박 쿠폰", "1", "숙박"],
      "example_invalid": ["CUP999 (목록에 없는 ID)", "100번 (범위 초과)", "abc (무효한 입력)"]
    }}
  }},
  
  "llm_execution_guide": {{
    "when_to_execute": "budget 수집 직후 자동 실행",
    "prerequisite": ["customer_name", "customer_phone", "travel_start_date", "travel_end_date", "budget"],
    "before_execution": "사용자에게 '사용 가능한 쿠폰을 확인하고 있습니다. 잠시만 기다려주세요...'라고 반드시 안내하세요",
    
    "api_call_detail": {{
      "method": "GET",
      "url": "/api/coupons?region=jeju&type=discount&start_date={{travel_start_date}}&end_date={{travel_end_date}}&budget={{budget}}",
      "parameters_from_collected": ["travel_start_date", "travel_end_date", "budget"],
      "parameter_mapping": {{
        "travel_start_date": "이전에 수집한 여행 시작 날짜를 YYYY-MM-DD 형식으로",
        "travel_end_date": "이전에 수집한 여행 종료 날짜를 YYYY-MM-DD 형식으로",
        "budget": "이전에 수집한 예산 금액을 숫자로"
      }},
      "example_call": "GET /api/coupons?region=jeju&type=discount&start_date=2025-08-01&end_date=2025-08-05&budget=70000",
      "expected_response": {{
        "format": "[{{coupon_id: 'CUP123', title: '제주도 숙박 10% 할인', discount_rate: 10, valid_until: '2025-08-31', min_amount: 50000}}, {{coupon_id: 'CUP124', title: '제주도 맛집 5% 할인', discount_rate: 5, valid_until: '2025-12-31', min_amount: 30000}}]",
        "fields": ["coupon_id (필수)", "title (필수)", "discount_rate", "valid_until", "min_amount"]
      }}
    }},
    
    "on_success": {{
      "action": "API 응답으로 받은 쿠폰 배열을 available_coupons 변수에 저장하세요",
      "display_format": "쿠폰 목록을 사용자에게 보기 좋게 제시하세요. 반드시 아래 형식을 사용하세요:\n\n🎁 사용 가능한 쿠폰\n\n1. {{title}}\n   • 할인: {{discount_rate}}%\n   • 유효기간: {{valid_until}}까지\n   • 최소금액: {{min_amount}}원\n\n2. {{title}}\n   • 할인: {{discount_rate}}%\n   • 유효기간: {{valid_until}}까지\n   • 최소금액: {{min_amount}}원\n\n",
      "emphasis": "각 쿠폰의 핵심 정보(이름, 할인율, 유효기간, 최소금액)를 명확하게 표시하세요",
      "then": "목록을 모두 출력한 후, selection_config.selection_prompt를 사용하여 사용자 선택을 유도하세요"
    }},
    
    "on_empty": {{
      "action": "조회 결과가 비어있을 때 처리",
      "message": "죄송합니다. 현재 입력하신 조건(날짜: {{travel_start_date}}~{{travel_end_date}}, 예산: {{budget}}원)에 맞는 쿠폰이 없습니다.",
      "allow_change": "날짜나 예산을 변경해보시겠어요? 아니면 다른 방법으로 도와드릴까요?",
      "options": ["날짜 변경", "예산 변경", "처음부터 다시"]
    }},
    
    "on_error": {{
      "action": "API 호출 실패 시 처리",
      "message": "쿠폰 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
      "retry": "다시 시도하시겠어요?",
      "fallback": "계속 오류가 발생하면 고객센터(1588-0000)로 문의해주세요"
    }},
    
    "selection_handling": {{
      "wait_for_user": true,
      "description": "사용자가 쿠폰을 선택할 때까지 서브봇은 대기합니다",
      "validation": "selection_config.selection_validation 참조",
      
      "on_valid_selection": {{
        "action": "유효한 선택을 받았을 때 처리",
        "save_to": "selected_coupon_id",
        "get_selected_name": "선택된 coupon_id로 available_coupons에서 title 찾기",
        "message": "'{{선택된 쿠폰명}}' 쿠폰을 선택하셨습니다. 상세 정보를 확인하겠습니다",
        "example": "사용자가 '1번' 선택 → available_coupons[0] 찾기 → coupon_id 저장 → '제주도 숙박 10% 할인' 쿠폰을 선택하셨습니다"
      }},
      
      "on_invalid_selection": {{
        "action": "무효한 선택을 받았을 때 처리",
        "message": "selection_config.selection_validation.on_invalid 메시지 사용",
        "retry": true,
        "show_list_again": "필요하면 쿠폰 목록을 다시 보여주세요"
      }}
    }},
    
    "return_to_main": {{
      "when": "사용자가 유효한 쿠폰을 선택하고 selected_coupon_id에 저장된 후",
      "return_data": {{
        "available_coupons": "조회된 전체 쿠폰 목록 배열",
        "selected_coupon_id": "사용자가 선택한 쿠폰의 ID (예: CUP123)"
      }},
      "next_action": "메인봇으로 복귀하여 다음 변수 수집으로 진행"
    }}
  }}
}}

📋 최종 출력 형식
<<<STEP3_START>>>
json{{
  "step": 3,
  "description": "선택된 기능 실행을 위한 변수 분류",
  "selected_function": {{
    "feature_id": "{{{{Step 2의 feature_id}}}}",
    "name": "{{{{Step 2의 name}}}}",
    "job_title": "{{{{Step 2의 job_title}}}}",
    "description": "{{{{Step 2의 description}}}}",
    "user_value": "{{{{Step 2의 user_value}}}}",
    "work_scenario": "{{{{Step 2의 work_scenario}}}}"
  }},
  
  "based_on_context": {{
    "분류명1": "값1",
    "분류명2": "값2",
    "분류명3": "값3",
    "분류명4": "값4",
    "분류명5": "값5"
  }},
  
  "business_plan": {{
    "service_type": "예약/약속형|즉시처리형|분석/검토형|배송/물류형|지속관리형",
    "final_goal": "이 서비스의 최종 목적",
    "service_workflow": {{
      "step1": {{
        "action": "구체적 행동",
        "purpose": "왜 필요한가",
        "stage": "A",
        "required_info": ["정보1", "정보2"]
      }},
      "step2": {{
        "action": "구체적 행동",
        "purpose": "왜 필요한가",
        "stage": "B",
        "required_info": ["정보3"]
      }}
      // ... (5-10단계)
    }}
  }},
  
  "webhook_spec": {{
    "endpoint": "/api/{{api_id}}",
    "method": "POST",
    "description": "서비스 최종 실행을 위한 Webhook"
  }},
  
  "all_variables": [
    {{
      "variable_id": "v001",
      "variable_name": "필드명",
      "description": "설명",
      "data_type": "String|Number|Boolean|Date|Array|Object",
      "category": "사용자 입력|API 호출",
      "example": "예시값",
      "why_this_category": "분류 이유"
    }}
    // ... (workflow 순서대로 모든 변수)
  ],
  
  "classification": {{
    "user_input_variables": [
      {{
        "variable_id": "v001",
        "variable_name": "customer_name",
        "question": "고객님 성함을 알려주세요",
        "data_type": "String",
        "is_mandatory": true,
        "validation_rule": "최소 2자 이상",
        
        "llm_execution_guide": {{
          "when_to_execute": "대화 시작 시",
          "prerequisite": "없음",
          "how_to_ask": "구체적인 질문 예시",
          "user_friendly_tone": "톤 가이드",
          
          "validation": {{
            "rule": "검증 규칙",
            "on_invalid": "오류 메시지",
            "auto_format": "자동 변환 (있으면)",
            "example_valid": ["예시1", "예시2"],
            "example_invalid": ["무효1", "무효2"]
          }},
          
          "after_collection": "다음 행동"
        }}
      }}
      // ... (선택 변수 제외한 모든 사용자 입력)
    ],
    
    "non_user_input_variables": [
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // 타입 A: 즉시 복귀형 서브봇
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      {{
        "variable_id": "v007",
        "variable_name": "coupon_details",
        "sub_bot_id": "coupon_detail_task",
        "sub_bot_name": "쿠폰 상세 조회",
        "api_endpoint": "/api/{{api_id}}_coupon_detail_task",
        "purpose": "선택된 쿠폰의 상세 조건 조회",
        "trigger_keyword": ["쿠폰 상세", "조건"],
        "source": "CouponServiceAPI",
        "why_not_ask_user": "쿠폰 조건은 동적으로 변함",
        
        "execution_logic": {{
          "step1": "API 호출",
          "step2": "결과 저장",
          "step3": "완료"
        }},
        
        "subbot_type": "direct_return",
        "requires_user_selection": false,
        
        "llm_execution_guide": {{
          "when_to_execute": "selected_coupon_id 수집 직후",
          "prerequisite": ["selected_coupon_id"],
          "before_execution": "안내 메시지",
          
          "api_call_detail": {{
            "method": "GET",
            "url": "API URL",
            "parameters_from_collected": ["변수들"],
            "parameter_mapping": {{"변수": "설명"}},
            "example_call": "예시",
            "expected_response": {{"format": "형식"}}
          }},
          
          "on_success": {{
            "action": "저장 및 처리",
            "display": "출력 여부 및 형식"
          }},
          
          "on_error": {{"message": "오류 메시지"}},
          
          "return_to_main": {{
            "when": "복귀 시점",
            "return_data": {{"변수": "설명"}},
            "next_action": "다음 행동"
          }}
        }}
      }},
      
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // 타입 B: 선택 대기형 서브봇
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      {{
        "variable_id": "v006",
        "variable_name": "available_coupons",
        "sub_bot_id": "coupon_query_task",
        "sub_bot_name": "쿠폰 목록 조회 및 선택",
        "api_endpoint": "/api/{{api_id}}_coupon_query_task",
        "purpose": "쿠폰 조회 및 선택",
        "trigger_keyword": ["쿠폰 리스트"],
        "source": "CouponServiceAPI",
        "why_not_ask_user": "실시간 조회 필요",
        
        "execution_logic": {{
          "step1": "API 호출",
          "step2": "결과 저장",
          "step3": "옵션 제시",
          "step4": "사용자 선택 대기",
          "step5": "선택 저장"
        }},
        
        "subbot_type": "selection_required",
        "requires_user_selection": true,
        
        "selection_config": {{
          "selection_variable": "selected_coupon_id",
          "selection_data_type": "String",
          "selection_prompt": "선택 유도 메시지",
          "selection_validation": {{
            "rule": "검증 규칙",
            "flexible_matching": {{
              "by_number": "숫자 매칭",
              "by_name": "이름 매칭",
              "by_id": "ID 매칭"
            }},
            "on_invalid": "무효 메시지",
            "example_valid": ["예시들"],
            "example_invalid": ["무효 예시들"]
          }}
        }},
        
        "llm_execution_guide": {{
          "when_to_execute": "실행 시점",
          "prerequisite": ["선행 변수들"],
          "before_execution": "안내 메시지",
          
          "api_call_detail": {{
            "method": "GET",
            "url": "API URL",
            "parameters_from_collected": ["변수들"],
            "example_call": "예시",
            "expected_response": {{"format": "형식"}}
          }},
          
          "on_success": {{
            "action": "저장 및 제시",
            "display_format": "출력 형식",
            "then": "선택 유도"
          }},
          
          "on_empty": {{
            "message": "결과 없을 때",
            "allow_change": "변경 옵션"
          }},
          
          "on_error": {{"message": "오류 메시지"}},
          
          "selection_handling": {{
            "wait_for_user": true,
            "on_valid_selection": {{
              "action": "유효 선택 처리",
              "message": "확인 메시지"
            }},
            "on_invalid_selection": {{
              "message": "무효 선택 메시지"
            }}
          }},
          
          "return_to_main": {{
            "when": "선택 완료 후",
            "return_data": {{
              "available_coupons": "목록",
              "selected_coupon_id": "선택된 ID"
            }},
            "next_action": "다음 행동"
          }}
        }}
      }}
    ]
  }},
  
  "summary": {{
    "total_variables": 9,
    "user_input_count": 5,
    "non_user_input_count": 4,
    "generated_sub_bots_count": 4,
    "subbot_type_breakdown": {{
      "direct_return": 3,
      "selection_required": 1
    }}
  }},
  
  "reselection_guide": "변수 분류를 수정하면 메인봇 질문과 서브봇 개수가 변경됩니다"
}}
<<<STEP3_END>>>

🚨 최종 체크리스트
생성 전 반드시 확인:
기본 필드:

 selected_function이 Step 2의 모든 필드를 포함하는가?
 business_plan의 service_workflow가 명확한가?
 all_variables가 workflow 순서대로 나열되었는가?

사용자 입력 변수:

 각 변수에 llm_execution_guide가 있는가?
 when_to_execute, prerequisite가 명확한가?
 how_to_ask에 구체적인 예시가 있는가?
 validation이 상세한가?
 example_valid, example_invalid가 3개 이상인가?
 after_collection이 명확한가?
 선택 변수는 포함하지 않았는가? (서브봇이 처리)

서브봇 변수:

 subbot_type이 명확한가? (direct_return / selection_required)
 requires_user_selection이 올바른가?
 execution_logic이 구체적인가?
 llm_execution_guide가 충분히 상세한가?
 api_call_detail에 example_call이 있는가?
 on_success, on_error, return_to_main이 모두 있는가?

선택 대기형 서브봇 (selection_required):

 selection_config가 포함되어 있는가?
 selection_variable이 명확한가?
 flexible_matching이 3가지 있는가? (by_number, by_name, by_id)
 selection_handling이 상세한가?
 return_data에 목록과 선택 결과 모두 포함되는가?

순서:

 all_variables가 workflow step 순서를 따르는가?
 서브봇 변수가 적절한 위치에 있는가?
 선택 기반 질문이 서브봇 다음에 있는가?

요약:

 summary의 숫자들이 정확한가?
 subbot_type_breakdown이 올바른가?

## 📦 파일 생성

위 3단계 결과를 각각 파일로 저장하세요.

**중요: 반드시 아래 XML 형식을 정확히 지켜주세요!**

<<<STEP1_START>>>
<file>
<filename>intermediate_step1.json</filename>
<content>
```json
{{
  "step": 1,
  "description": "5가지 분류 및 각 분류별 세부 옵션",
  ...
  (STEP1의 전체 JSON 내용)
}}
```
</content>
</file>
<<<STEP1_END>>>

<<<STEP2_START>>>
<file>
<filename>intermediate_step2.json</filename>
<content>
```json
{{
  "step": 2,
  "description": "선택된 조건에 맞는 서비스 직원 봇 역할 20가지",
  ...
  (STEP2의 전체 JSON 내용)
}}
```
</content>
</file>
<<<STEP2_END>>>

<<<STEP3_START>>>
<file>
<filename>intermediate_step3.json</filename>
<content>
```json
{{
  "step": 3,
  "description": "선택된 기능 실행을 위한 변수 분류",
  ...
  (STEP3의 전체 JSON 내용)
}}
```
</content>
</file>
<<<STEP3_END>>>

---

**필수 체크:**
1. 각 STEP은 <<<STEPN_START>>>와 <<<STEPN_END>>> 사이에 위치
2. 각 파일은 <file> 태그로 감싸기
3. <filename> 태그에 파일명 명시
4. <content> 태그 안에 실제 JSON 내용
5. 3개 파일만 생성 (main_task_config.json 등은 만들지 마세요)
6. JSON 내용은 완전해야 함 (요약 금지, ... 사용 금지)
"""
    
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    llm_response_text = send_llm_request_xml(messages, botjob=True, use_hf=True)
    
    # 파일 저장
    result  = save_bot_design_files(llm_response_text, category_id)
    
    return {
        "raw_response": llm_response_text,
        "saved_files": result["saved_files"],
        "step3_json": result["step3_json"]  # ✅ 추가!
    }


def generate_complete_bot_design(
    room_id: str, 
    category_id: str, 
    step3_json: dict, 
    subbot_list: list,
    bot_db , # BotDatabase 인스턴스
    session_manager  
):
    """
    Step 3 JSON을 기반으로 기존 시스템과 호환되는 봇 파일 생성 + DB 저장
    
    Args:
        room_id: 방 ID (예: "room_001")
        category_id: 카테고리 ID (예: "쇼핑_구매")
        step3_json: Step 3 설계 JSON
        subbot_list: 서브봇 리스트
        bot_db: BotDatabase 인스턴스
    
    Returns:
        dict: 생성 결과
    """
    
    print("=" * 80)
    print("🚀 기존 시스템 호환 봇 파일 생성 시작")
    print(f"   방 ID: {room_id}")
    print(f"   카테고리: {category_id}")
    print(f"   서브봇 개수: {len(subbot_list)}")
    print("=" * 80)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 메인봇 ID 생성
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    main_bot_id = f"{category_id}_main_task"
    
    print(f"\n📝 메인봇 ID: {main_bot_id}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 메인봇 JSON 생성
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    main_bot_json = convert_step3_to_main_bot_json(
        main_bot_id,
        step3_json,
        subbot_list
    )
    
    print(f"\n✅ 메인봇 JSON 생성 완료")
    print(f"   필드 개수: {len(main_bot_json['data_schema'])}")
    print(f"   완료 조건: {len(main_bot_json['completion_condition']['must_fill'])}개 필드")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 메인봇 프롬프트 생성
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    main_bot_prompt = generate_main_bot_prompt(step3_json, subbot_list)
    
    print(f"\n✅ 메인봇 프롬프트 생성 완료")
    print(f"   길이: {len(main_bot_prompt)} chars")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 서브봇 파일들 생성
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    subbot_files = []

    # ✅ classification에서 non_user_input_variables 가져오기
    classification = step3_json.get("classification", {})
    non_user_input_vars = classification.get("non_user_input_variables", [])

    for subbot_var in non_user_input_vars:
        print(f"\n📦 서브봇 생성 중: {subbot_var.get('sub_bot_id', '')}")
        
        # 서브봇 JSON 생성 (통째로 복사 방식)
        subbot_json = generate_subbot_json(subbot_var, step3_json)
        
        # 서브봇 프롬프트 생성 (llm_execution_guide 기반)
        subbot_prompt = generate_subbot_prompt(subbot_var)
        
        subbot_files.append({
            'bot_id': subbot_var.get('sub_bot_id', ''),
            'json': subbot_json,
            'prompt': subbot_prompt
        })
        
        print(f"   ✅ {subbot_var.get('sub_bot_name', '')} 생성 완료")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. 파일 시스템에 저장
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    base_dir = Path(f"bot_designs/{category_id}")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 메인봇 파일 저장
    main_bot_json_path = base_dir / f"{main_bot_id}.json"
    main_bot_prompt_path = base_dir / f"{main_bot_id}_prompt.txt"
    
    with open(main_bot_json_path, 'w', encoding='utf-8') as f:
        json.dump(main_bot_json, f, ensure_ascii=False, indent=2)
    
    with open(main_bot_prompt_path, 'w', encoding='utf-8') as f:
        f.write(main_bot_prompt)
    
    print(f"\n💾 메인봇 파일 저장:")
    print(f"   JSON: {main_bot_json_path}")
    print(f"   TXT: {main_bot_prompt_path}")
    
    # 서브봇 파일 저장
    saved_subbot_paths = []
    for subbot_file in subbot_files:
        bot_id = subbot_file['bot_id']
        
        json_path = base_dir / f"{bot_id}.json"
        prompt_path = base_dir / f"{bot_id}_prompt.txt"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(subbot_file['json'], f, ensure_ascii=False, indent=2)
        
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(subbot_file['prompt'])
        
        saved_subbot_paths.append({
            'bot_id': bot_id,
            'json_path': str(json_path),
            'prompt_path': str(prompt_path)
        })
        
        print(f"\n💾 서브봇 파일 저장: {bot_id}")
        print(f"   JSON: {json_path}")
        print(f"   TXT: {prompt_path}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. DB에 메인봇 저장 (수정됨)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n🗄️  DB에 메인봇 저장 중...")

    try:
        # 🚀 [수정] create_bot → register_bot_file
        bot_db.register_bot_file(
            bot_id=main_bot_id,
            bot_name=step3_json['selected_function']['name'],
            bot_type='main',  # 'main' 타입 사용
            definition_file_path=str(main_bot_json_path),
            prompt_file_path=str(main_bot_prompt_path)
        )
        print(f"   ✅ 메인봇 DB 저장 완료: {main_bot_id}")
    except Exception as e:
        print(f"   ⚠️  메인봇 DB 저장 실패: {e}")
        # 이미 존재하면 업데이트
        try:
            bot_db.update_bot_metadata(
                bot_id=main_bot_id,
                bot_name=step3_json['selected_function']['name'],
                is_active=1
            )
            print(f"   ✅ 메인봇 DB 업데이트 완료: {main_bot_id}")
        except Exception as e2:
            print(f"   ❌ 메인봇 DB 업데이트 실패: {e2}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. DB에 서브봇들 저장 (수정됨)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    for subbot_path in saved_subbot_paths:
        bot_id = subbot_path['bot_id']
        
        # 서브봇 이름 찾기
        subbot_name = next(
            (s['sub_bot_name'] for s in subbot_list if s['sub_bot_id'] == bot_id),
            bot_id
        )
        
        try:
            # 🚀 [수정] create_bot → register_bot_file
            bot_db.register_bot_file(
                bot_id=bot_id,
                bot_name=subbot_name,
                bot_type='service',  # ⚠️ 주의: 서브봇은 'service' 타입
                definition_file_path=subbot_path['json_path'],
                prompt_file_path=subbot_path['prompt_path']
            )
            print(f"   ✅ 서브봇 DB 저장 완료: {bot_id}")
        except Exception as e:
            print(f"   ⚠️  서브봇 DB 저장 실패 ({bot_id}): {e}")
            # 이미 존재하면 업데이트
            try:
                bot_db.update_bot_metadata(
                    bot_id=bot_id,
                    bot_name=subbot_name,
                    is_active=1
                )
                print(f"   ✅ 서브봇 DB 업데이트 완료: {bot_id}")
            except Exception as e2:
                print(f"   ❌ 서브봇 DB 업데이트 실패 ({bot_id}): {e2}")
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 8. DB에 방(Room) 생성/업데이트 (수정됨)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n🏠 DB에 방 저장 중: {room_id}")

    try:
        # 먼저 기존 방이 있는지 확인
        existing_room = bot_db.get_room(room_id)
        
        if existing_room:
            # 기존 방이 있으면 업데이트
            print(f"   ℹ️  기존 방 발견, main_bot_id 업데이트 중...")
            print(f"      이전: {existing_room['main_bot_id']}")
            print(f"      변경: {main_bot_id}")
            
            bot_db.update_room(
                room_id=room_id,
                main_bot_id=main_bot_id
            )
            print(f"   ✅ 방 업데이트 완료: {room_id} → {main_bot_id}")
        else:
            # 새 방 생성
            bot_db.create_room(
                room_id=room_id,
                room_name=f"{category_id} 방",
                main_bot_id=main_bot_id
            )
            print(f"   ✅ 방 생성 완료: {room_id} → {main_bot_id}")
            
    except Exception as e:
        print(f"   ❌ 방 저장/업데이트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 9. ConfigManager 리로드
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n🔄 ConfigManager 리로드 중...")
    try:
        # from ragmanager import config_manager
        config_manager.load_from_database(bot_db)
        print(f"   ✅ ConfigManager 리로드 완료")
        print(f"   로드된 봇: {len(config_manager.bots)}개")
        print(f"   로드된 방: {len(config_manager.rooms)}개")
    except Exception as e:
        print(f"   ⚠️  ConfigManager 리로드 실패: {e}")
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 10. 🆕 해당 방의 모든 세션 초기화
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n🔄 방 {room_id}의 세션 초기화 중...")
    try:
        cleared_count = session_manager.clear_room_sessions(room_id)
        print(f"   ✅ {cleared_count}개 세션 초기화 완료")
        print(f"   💡 사용자가 다음 메시지 전송 시 새 메인봇({main_bot_id})으로 세션 생성됨")
    except Exception as e:
        print(f"   ⚠️  세션 초기화 실패: {e}")
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 10. 결과 반환
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n" + "=" * 80)
    print("✅ 봇 생성 완료!")
    print(f"   메인봇: {main_bot_id}")
    print(f"   서브봇: {len(subbot_files)}개")
    print(f"   방: {room_id}")
    print("=" * 80)
    
    return {
        "success": True,
        "main_bot": {
            "bot_id": main_bot_id,
            "json_path": str(main_bot_json_path),
            "prompt_path": str(main_bot_prompt_path)
        },
        "subbots": saved_subbot_paths,
        "room": {
            "room_id": room_id,
            "main_bot_id": main_bot_id
        }
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
def auto_fill_test_data(session, bot_id: str, config_manager) -> dict:
    """
    테스트용: 현재 봇의 모든 필드를 example 값으로 자동 채우기
    
    사용자가 "자동"이라고 입력하면 실행
    
    Args:
        session: SessionStateManager 인스턴스
        bot_id: 현재 활성 봇 ID
        config_manager: ConfigManager 인스턴스
        
    Returns:
        dict: {
            'filled_count': 채워진 필드 수,
            'filled_fields': 채워진 필드 목록,
            'skipped_count': 스킵된 필드 수,
            'message': 사용자에게 보여줄 메시지
        }
    """
    import json
    
    print(f"\n{'='*60}")
    print(f"🤖 [Auto Fill] 자동 데이터 채우기 시작")
    print(f"   봇 ID: {bot_id}")
    print(f"{'='*60}\n")
    
    # 봇 설정 가져오기
    bot_config = config_manager.get_bot_config(bot_id)
    if not bot_config:
        return {
            'filled_count': 0,
            'filled_fields': [],
            'skipped_count': 0,
            'message': f"❌ 봇 {bot_id}를 찾을 수 없습니다."
        }
    
    filled_fields = []
    filled_count = 0
    skipped_count = 0
    
    print(f"   📋 전체 필드: {len(bot_config.data_schema)}개\n")
    
    # 모든 필드 순회
    for field_info in bot_config.data_schema:
        field_name = field_info.get('field_name')
        is_mandatory = field_info.get('is_mandatory', False)
        current_value = session.shared_context.get(field_name)
        
        # 이미 값이 있으면 스킵
        if current_value is not None and str(current_value).strip():
            print(f"   ⏭️  {field_name}: 이미 값 존재")
            skipped_count += 1
            continue
        
        # example 값 가져오기
        example_value = field_info.get('example', '')
        
        if not example_value:
            print(f"   ⚠️  {field_name}: example 값 없음, 스킵")
            skipped_count += 1
            continue
        
        # 🔥 JSON 문자열 파싱
        final_value = example_value
        display_value = str(example_value)
        
        if isinstance(example_value, str):
            trimmed = example_value.strip()
            # JSON 배열/객체 판별
            if trimmed.startswith('[') or trimmed.startswith('{'):
                try:
                    # JSON 파싱 - 배열/객체 전체 저장
                    final_value = json.loads(example_value)
                    
                    if isinstance(final_value, list):
                        display_value = f"[배열 {len(final_value)}개]"
                        print(f"   ✅ {field_name} = [배열 {len(final_value)}개] {'(필수)' if is_mandatory else ''}")
                    elif isinstance(final_value, dict):
                        display_value = f"[객체 {len(final_value)}개 키]"
                        print(f"   ✅ {field_name} = [객체 {len(final_value)}개] {'(필수)' if is_mandatory else ''}")
                    
                except json.JSONDecodeError:
                    # 파싱 실패 - 문자열 그대로
                    display_value = example_value[:50]
                    if len(example_value) > 50:
                        display_value += "..."
                    print(f"   ✅ {field_name} = {display_value} {'(필수)' if is_mandatory else ''}")
            else:
                # 일반 문자열/숫자
                display_value = example_value
                print(f"   ✅ {field_name} = {example_value} {'(필수)' if is_mandatory else ''}")
        
        # 세션에 저장
        session.shared_context[field_name] = final_value
        
        filled_fields.append({
            'field': field_name,
            'value': display_value,
            'type': type(final_value).__name__,
            'mandatory': is_mandatory
        })
        filled_count += 1
    
    # 결과 메시지 생성
    if filled_count == 0:
        if skipped_count > 0:
            message = f"ℹ️  채울 필드가 없습니다.\n({skipped_count}개 필드는 이미 값이 있거나 example이 없음)"
        else:
            message = "❌ 채울 수 있는 필드가 없습니다."
    else:
        # 필드 요약 (최대 10개만 표시)
        field_summary = "\n".join([
            f"  • {f['field']}: {f['value']}" 
            for f in filled_fields[:10]
        ])
        
        if len(filled_fields) > 10:
            field_summary += f"\n  ... 외 {len(filled_fields) - 10}개"
        
        message = f"""✅ 자동 입력 완료! {filled_count}개 필드가 채워졌습니다.

📊 채워진 데이터:
{field_summary}"""
        
        if skipped_count > 0:
            message += f"\n\n⏭️  스킵: {skipped_count}개"
    
    print(f"\n{'='*60}")
    print(f"✅ [Auto Fill] 완료")
    print(f"   채워진 필드: {filled_count}개")
    print(f"   스킵된 필드: {skipped_count}개")
    print(f"{'='*60}\n")
    
    return {
        'filled_count': filled_count,
        'filled_fields': filled_fields,
        'skipped_count': skipped_count,
        'message': message
    }


def convert_step3_to_main_bot_json(
    main_bot_id: str,
    step3_json: dict,
    subbot_list: list
) -> dict:
    """
    step3_json → 메인봇 JSON 변환
    
    핵심 원칙:
    1. classification.user_input_variables를 통째로 복사
    2. classification.non_user_input_variables를 통째로 복사
    3. 파싱/재조립 금지
    4. workflow 무시, classification 순서만 따름
    """
    
    classification = step3_json.get("classification", {})
    user_input_vars = classification.get("user_input_variables", [])
    non_user_input_vars = classification.get("non_user_input_variables", [])
    must_fill = classification.get("total_info_needed", [])
    selected_function = step3_json.get("selected_function", {})
    webhook_spec = step3_json.get("webhook_spec", {})
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ data_schema 구성 (통째로 복사!)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    data_schema = []
    
    # A. user_input_variables 통째로 복사
    for var in user_input_vars:
        # 원본 객체를 그대로 복사
        field = dict(var)  # 얕은 복사
        
        # field_type만 추가 (원본에 없으므로)
        field['field_type'] = 'user_input'
        
        data_schema.append(field)
    
    # B. non_user_input_variables 통째로 복사
    for var in non_user_input_vars:
        # 원본 객체를 그대로 복사
        field = dict(var)
        
        # field_type만 추가
        field['field_type'] = 'subbot_result'
        
        data_schema.append(field)
        
        # 완료 플래그 추가
        data_schema.append({
            "field_name": f"{var['variable_name']}_completed",
            "description": f"{var.get('sub_bot_name', '')} 완료 여부",
            "is_mandatory": True,
            "field_type": "subbot_flag",
            "subbot_id": var.get("sub_bot_id", ""),
            "llm_instructions": {
                "automatic": "시스템이 자동으로 관리합니다. LLM은 수정하지 마세요"
            }
        })
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ completion_condition
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # must_fill = []
    
    # # 필수 사용자 입력 변수
    # for var in user_input_vars:
    #     if var.get("is_mandatory", False):
    #         must_fill.append(var["variable_name"])
    
    # # 모든 서브봇 완료 플래그
    # for var in non_user_input_vars:
    #     must_fill.append(f"{var['variable_name']}_completed")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ subbot_mapping (통째로 복사!)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    subbot_mapping = {}
    
    for var in non_user_input_vars:
        subbot_id = var.get("sub_bot_id", "")
        
        # 원본 정보를 통째로 사용
        subbot_mapping[subbot_id] = {
            # 기본 정보
            "variable_name": var["variable_name"],
            "sub_bot_name": var.get("sub_bot_name", ""),
            "purpose": var.get("purpose", ""),
            "subbot_type": var.get("subbot_type", "direct_return"),
            "requires_user_selection": var.get("requires_user_selection", False),
            
            # 트리거 정보
            "trigger_keywords": var.get("trigger_keyword", []),
            "api_endpoint": var.get("api_endpoint", ""),
            
            # ✅ 핵심: 원본 정보 통째로 포함!
            "execution_logic": var.get("execution_logic", {}),
            "selection_config": var.get("selection_config"),
            "llm_execution_guide": var.get("llm_execution_guide", {}),
            
            # 추가 메타데이터
            "source": var.get("source", ""),
            "why_not_ask_user": var.get("why_not_ask_user", "")
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4️⃣ call_triggers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    call_triggers = {}
    
    for var in non_user_input_vars:
        subbot_id = var.get("sub_bot_id", "")
        keywords = var.get("trigger_keyword", [])
        
        for keyword in keywords:
            call_triggers[keyword] = subbot_id
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5️⃣ 최종 JSON
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    return {
        "bot_id": main_bot_id,
        "task_name": selected_function.get("name", ""),
        "job_title": selected_function.get("job_title", ""),
        "service_type": step3_json.get("business_plan", {}).get("service_type", ""),
         "service_workflow": step3_json.get("business_plan", {}).get("service_workflow", {}),

        "all_variables": step3_json.get("all_variables",[]),

        "final_goal": step3_json.get("business_plan", {}).get("final_goal", ""),
        
        # ✅ 핵심: 통째로 복사된 data_schema
        "data_schema": data_schema,
        
        "completion_condition": {
            "must_fill": must_fill
        },
        
        # ✅ 핵심: 통째로 복사된 subbot_mapping
        "subbot_mapping": subbot_mapping,
        
        "call_triggers": call_triggers,
        
        "response_rules": {
            "allowed_action_types": [
                "update_data",
                "call_subbot",
                "complete_task"
            ],
            "절대_규칙": {
                "rule1": "이미 채워진 필드는 절대 다시 묻지 마세요",
                "rule2": "다음 빈 필드만 질문하세요",
                "rule3": "서브봇 호출은 call_subbot 액션만 사용하세요",
                "rule4": "한 번에 하나의 필드만 처리하세요",
                "rule5": "JSON 형식 사용 금지, 오직 XML만 사용하세요"
            },
            "작업_완료_조건": {
                "instruction": "다음 필드들이 모두 채워지면 complete_task 액션을 사용하여 작업을 완료하세요",
                "fields": must_fill,
                "completion_xml": f"""<bot_response>
  <message>모든 정보가 확인되었습니다! {selected_function.get("name", "")}을(를) 완료합니다.</message>
  <actions>
    <action type="complete_task">
      <summary>{selected_function.get("name", "")} 정보 수집 완료</summary>
    </action>
  </actions>
</bot_response>"""
            }
        },
        
        "webhook_spec": {
            "endpoint": webhook_spec.get("endpoint", ""),
            "method": webhook_spec.get("method", "POST"),
            "description": webhook_spec.get("description", "")
        },
        
        "summary": {
            "total_variables": len(user_input_vars) + len(non_user_input_vars),
            "user_input_count": len(user_input_vars),
            "non_user_input_count": len(non_user_input_vars),
            "generated_sub_bots_count": len(non_user_input_vars),
            "subbot_type_breakdown": _count_subbot_types(non_user_input_vars)
        }
    }

def generate_main_bot_prompt(step3_json: dict, subbot_list: list) -> str:
    """
    메인봇 기본 프롬프트 생성 (역할 + 규칙만)
    
    변수별 상세 가이드는 build_xml_system_prompt()에서 동적 추가
    """
    
    task_name = step3_json.get("selected_function", {}).get("name", "")
    job_title = step3_json.get("selected_function", {}).get("job_title", "")
    final_goal = step3_json.get("business_plan", {}).get("final_goal", "")
    service_type = step3_json.get("business_plan", {}).get("service_type", "")
    
    # 최소한의 정적 프롬프트만
    prompt = f"""[SYSTEM INSTRUCTION]
당신은 {task_name} 임무를 수행하는 스마트 데이터 수집 에이전트입니다.
직책: {job_title}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 핵심 역할
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**최종 목표:** {final_goal}
**서비스 유형:** {service_type}

1. 사용자로부터 필요한 정보를 하나씩 수집
2. 각 정보를 검증하고 XML 형식으로 저장
3. 필요한 시점에 서브봇을 호출하여 API 데이터 수집
4. 모든 필수 정보가 모이면 작업 완료

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 절대 규칙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 이미 채워진 필드는 절대 다시 묻지 마세요
2. <next_question>에 명시된 필드만 질문하세요
3. 서브봇 호출은 <action type="call_subbot"> 사용
4. 한 번에 하나의 필드만 처리
5. JSON 형식 사용 금지 - 오직 XML만 사용

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 사용 가능한 액션
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- update_data: 사용자 입력 저장
- call_subbot: 서브봇 호출
- complete_task: 작업 완료
"""
    
    return prompt



def _count_subbot_types(non_user_input_vars: list) -> dict:
    """서브봇 타입별 개수 집계"""
    breakdown = {}
    for var in non_user_input_vars:
        subbot_type = var.get("subbot_type", "direct_return")
        breakdown[subbot_type] = breakdown.get(subbot_type, 0) + 1
    return breakdown


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 서브봇 JSON 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_subbot_json(subbot_var: dict, step3_json: dict) -> dict:
    """
    서브봇 JSON 생성
    
    핵심 원칙:
    1. subbot_var 객체를 통째로 사용
    2. 파싱/재조립 금지
    """
    
    variable_name = subbot_var["variable_name"]
    subbot_id = subbot_var.get("sub_bot_id", "")

    subbot_type = subbot_var.get("subbot_type", "direct_return")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ data_schema (통째로 복사!)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    data_schema = []
    
    # A. 메인 결과 필드 (원본 통째로)
    result_field = dict(subbot_var)  # 통째로 복사
    result_field['field_type'] = 'subbot_result'
    result_field['is_mandatory'] = True
    
    # all_variables에서 example 찾기 (추가 정보만)
    import json
    example_value = ''
    for all_var in step3_json.get('all_variables', []):
        if all_var.get('variable_name') == variable_name:
            example_value = all_var.get('example', '')
            break
    
    if isinstance(example_value, (list, dict)):
        example_value = json.dumps(example_value, ensure_ascii=False)
    
    result_field['example'] = example_value
    
    data_schema.append(result_field)
    
    # B. 완료 플래그
    data_schema.append({
        "field_name": f"{variable_name}_completed",
        "description": "작업 완료 여부",
        "is_mandatory": True,
        "field_type": "completion_flag",
        "default_value": False,
        "llm_instructions": {
            "automatic": "시스템이 자동으로 관리합니다. LLM은 수정하지 마세요"
        }
    })
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ prompt_template (llm_execution_guide 활용)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    llm_guide = subbot_var.get("llm_execution_guide", {})
    
    prompt_parts = [
        f"# {subbot_var.get('sub_bot_name', '')}",
        "",
        f"## 목적",
        subbot_var.get("purpose", ""),
        "",
        f"## 실행 시점",
        llm_guide.get("when_to_execute", ""),
        ""
    ]
    
    # 선행 조건
    prerequisite = llm_guide.get("prerequisite", [])
    if prerequisite:
        prompt_parts.extend([
            "## 선행 조건",
            f"다음 필드들이 먼저 수집되어야 합니다: {', '.join(prerequisite)}",
            ""
        ])
    
    # 실행 전 안내
    before_msg = llm_guide.get("before_execution", "")
    if before_msg:
        prompt_parts.extend([
            "## 실행 전 안내",
            before_msg,
            ""
        ])
    
    # API 호출 상세
    api_detail = llm_guide.get("api_call_detail", {})
    if api_detail:
        prompt_parts.extend([
            "## API 호출 정보",
            f"- Method: {api_detail.get('method', '')}",
            f"- URL: {api_detail.get('url', '')}",
            f"- 예시: {api_detail.get('example_call', '')}",
            ""
        ])
    
    prompt_template = "\n".join(prompt_parts)



    return_data = llm_guide.get("return_to_main", {}).get("return_data", {})

    # return_data의 키들을 리스트로 추출
    return_data_keys = list(return_data.keys()) if return_data else []

    # variable_name_completed 추가
    must_fill_list = return_data_keys
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ 최종 JSON
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    return {
        "bot_id": subbot_id,
        "task_name": subbot_var.get("sub_bot_name", ""),
        "subbot_type": subbot_type,
        "is_subbot": True,
        
        "prompt_template": prompt_template,
        
        # ✅ 핵심: 통째로 복사된 data_schema
        "data_schema": data_schema,
        
        "completion_condition": {
            "must_fill": must_fill_list  
        },
        
        "activation_conditions": {
            "mission_required": False
        },
        
        # ✅ 원본 정보 전체 포함
        "api_endpoint": subbot_var.get("api_endpoint", ""),
        "trigger_keywords": subbot_var.get("trigger_keyword", []),
        "execution_logic": subbot_var.get("execution_logic", {}),
        "selection_config": subbot_var.get("selection_config"),
        "llm_execution_guide": llm_guide,
        
        "call_triggers": {}
    }


def generate_subbot_prompt(subbot: dict) -> str:
    """
    서브봇 프롬프트 생성 (타입별 차별화)
    
    Args:
        subbot: classification.non_user_input_variables의 항목
    """
    subbot_type = subbot.get("subbot_type", "direct_return")
    llm_guide = subbot.get("llm_execution_guide", {})
    api_detail = llm_guide.get("api_call_detail", {})
    on_success = llm_guide.get("on_success", {})
    on_empty = llm_guide.get("on_empty", {})
    on_error = llm_guide.get("on_error", {})
    return_to_main = llm_guide.get("return_to_main", {})
    
    # 공통 헤더
    prompt = f"""[SYSTEM INSTRUCTION]
당신은 {subbot['sub_bot_name']} 임무를 수행하는 서브봇입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 임무 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**서브봇 타입:** {subbot_type}
**역할:** {subbot['purpose']}
**데이터 출처:** {subbot.get('source', '')}
**사용자에게 묻지 않는 이유:** {subbot.get('why_not_ask_user', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 API 호출 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**메서드:** {api_detail.get('method', '')}
**URL:** {api_detail.get('url', '')}
**파라미터:** {', '.join(api_detail.get('parameters_from_collected', []))}
**예시 호출:** {api_detail.get('example_call', '')}

**예상 응답 형식:**
{api_detail.get('expected_response', {}).get('format', '')}

"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 타입 A: 즉시 복귀형
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if subbot_type == "direct_return":
        prompt += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 실행 절차 (즉시 복귀형)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **API 호출 실행**
   - {api_detail.get('method', '')} {api_detail.get('url', '')}
   - 파라미터를 메인봇에서 전달받은 값으로 채워서 호출하세요

2. **응답 처리**
   - 성공 시: {on_success.get('action', '')}
   - 오류 시: {on_error.get('message', '')}

3. **결과 저장**
   - '{subbot['variable_name']}'에 API 응답 데이터 저장
   - '{subbot['variable_name']}_completed'를 true로 설정

4. **메인봇 복귀**
   - {return_to_main.get('when', '')}
   - 다음 행동: {return_to_main.get('next_action', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 XML 응답 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**작업 성공:**
<bot_response>
  <message>{subbot['sub_bot_name']}이 완료되었습니다!</message>
  <actions>
    <action type="update_data">
      <field>{subbot['variable_name']}</field>
      <value>{{API_응답_데이터}}</value>
      <validated>true</validated>
    </action>
    <action type="update_data">
      <field>{subbot['variable_name']}_completed</field>
      <value>true</value>
      <validated>true</validated>
    </action>
    <action type="complete_task">
      <summary>{subbot['sub_bot_name']} 완료</summary>
    </action>
  </actions>
</bot_response>

**작업 실패:**
<bot_response>
  <message>{on_error.get('message', '작업 중 오류가 발생했습니다')}</message>
  <actions>
    <action type="update_data">
      <field>{subbot['variable_name']}_completed</field>
      <value>false</value>
      <validated>true</validated>
      <reason>{{오류_원인}}</reason>
    </action>
    <action type="complete_task">
      <summary>{subbot['sub_bot_name']} 실패</summary>
    </action>
  </actions>
</bot_response>
"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 타입 B: 선택 대기형
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif subbot_type == "selection_required":
        selection_config = subbot.get("selection_config", {})
        selection_handling = llm_guide.get("selection_handling", {})
        
        prompt += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 실행 절차 (선택 대기형)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **API 호출 실행**
   - {api_detail.get('method', '')} {api_detail.get('url', '')}
   - 파라미터를 메인봇에서 전달받은 값으로 채워서 호출하세요

2. **응답 처리 및 제시**
   - 성공 시: {on_success.get('action', '')}
   - 목록 형식: {on_success.get('display_format', '')}
   - 결과가 비어있으면: {on_empty.get('message', '')}

3. **사용자 선택 대기**
   - 선택 프롬프트: "{selection_config.get('selection_prompt', '')}"
   - 선택 변수: {selection_config.get('selection_variable', '')}
   - 유연한 매칭 지원:
     • 번호: {selection_config.get('selection_validation', {}).get('flexible_matching', {}).get('by_number', '')}
     • 이름: {selection_config.get('selection_validation', {}).get('flexible_matching', {}).get('by_name', '')}
     • ID: {selection_config.get('selection_validation', {}).get('flexible_matching', {}).get('by_id', '')}

4. **선택 검증**
   - 유효한 선택: {selection_handling.get('on_valid_selection', {}).get('message', '')}
   - 무효한 선택: {selection_handling.get('on_invalid_selection', {}).get('message', '')}

5. **결과 저장 및 복귀**
   - '{subbot['variable_name']}'에 전체 목록 저장
   - '{selection_config.get('selection_variable', '')}'에 선택된 ID 저장
   - '{subbot['variable_name']}_completed'를 true로 설정

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 XML 응답 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**목록 제시:**
<bot_response>
  <message>{on_success.get('display_format', '목록을 제시합니다')}

{selection_config.get('selection_prompt', '')}</message>
  <actions>
    <action type="update_data">
      <field>{subbot['variable_name']}</field>
      <value>{{API_응답_배열}}</value>
      <validated>true</validated>
    </action>
  </actions>
</bot_response>

**유효한 선택:**
<bot_response>
  <message>{selection_handling.get('on_valid_selection', {}).get('message', '선택이 확인되었습니다')}</message>
  <actions>
    <action type="update_data">
      <field>{selection_config.get('selection_variable', '')}</field>
      <value>{{선택된_ID}}</value>
      <validated>true</validated>
    </action>
    <action type="update_data">
      <field>{subbot['variable_name']}_completed</field>
      <value>true</value>
      <validated>true</validated>
    </action>
    <action type="complete_task">
      <summary>{subbot['sub_bot_name']} 완료</summary>
    </action>
  </actions>
</bot_response>

**무효한 선택:**
<bot_response>
  <message>{selection_config.get('selection_validation', {}).get('on_invalid', '다시 선택해주세요')}</message>
  <actions>
    <action type="update_data">
      <field>{selection_config.get('selection_variable', '')}</field>
      <value>{{사용자_입력}}</value>
      <validated>false</validated>
      <reason>목록에 없는 항목</reason>
    </action>
  </actions>
</bot_response>

**목록이 비어있을 때:**
<bot_response>
  <message>{on_empty.get('message', '조건에 맞는 항목이 없습니다')}</message>
  <actions>
    <action type="update_data">
      <field>{subbot['variable_name']}_completed</field>
      <value>false</value>
      <validated>true</validated>
      <reason>조회 결과 없음</reason>
    </action>
    <action type="complete_task">
      <summary>{subbot['sub_bot_name']} 완료 (결과 없음)</summary>
    </action>
  </actions>
</bot_response>
"""
    
    # 공통 푸터
    prompt += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 중요 사항
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- 자동으로 실행되는 봇입니다 (메인봇에서 호출)
- 반드시 완료 플래그를 설정하세요
- XML 형식을 정확히 지켜주세요
- 사용 가능한 액션: update_data, complete_task 만
- JSON 형식 사용 금지
"""
    
    return prompt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🆕 봇 관리 명령어 처리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bot_creation_sessions = {}

def create_text_response(content):
    """일반 텍스트 응답"""
    return {
        "type": "text",
        "content": content
    }

config_manager = ConfigManager()
session_manager = None

def process_user_message(room_id, member_id, user_msg, extra_data=None):
    """
    순수 비즈니스 로직 - HTTP/WebSocket 무관
    
    Returns:
        dict: {
            'reply': dict or str,
            'bot_info': dict,
            'task_session_id': str,
            'bot_changed': bool,
            'completed': bool,
            'error': str (optional)
        }
    """
    
    print("kjdkghfdkjghksdfhkgdfsg")

    # 입력 검증
    if not room_id or not member_id:
        return {
            'error': 'missing_parameters',
            'reply': {'type': 'text', 'message': 'room_id와 member_id는 필수입니다.'},
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    session_key = f"{room_id}:{member_id}"
    print(f"\n[명령어] {user_msg}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 봇 목록 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg in ["봇목록", "봇 목록", "bot list", "/bots"]:
        bots = bot_db.get_all_bots(active_only=True)
        response = create_bot_list_response(bots)
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 봇 선택 → 상세 보기
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇선택:"):
        bot_id = user_msg.split(":", 1)[1]
        bot_meta = bot_db.get_bot(bot_id)
        
        if bot_meta:
            response = create_bot_detail_response(bot_meta)
        else:
            response = create_text_response(f"❌ 봇 '{bot_id}'를 찾을 수 없습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 봇 생성 시작
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg in ["봇생성", "봇 생성", "create bot", "/create"]:
        bot_creation_sessions[session_key] = {
            "stage": "step1",
            "data": {}
        }
        
        response = {
            "type": "bot_management",
            "widget_type": "bot_creation_step1",
            "content": "어떤 서비스의 봇을 만들까요?",
            "service_categories": [
                {
                    "id": "shopping",
                    "icon": "🛒",
                    "title": "쇼핑/구매",
                    "description": "상품 추천부터 주문까지",
                    "examples": "상품 추천, 장바구니, 주문 확인, 배달 조회"
                },
                {
                    "id": "travel_food",
                    "icon": "✈️",
                    "title": "여행/맛집",
                    "description": "예약하고 추천받고",
                    "examples": "호텔 예약, 맛집 추천, 여행 일정, 식당 예약"
                },
                {
                    "id": "consultation",
                    "icon": "💬",
                    "title": "상담/정보",
                    "description": "궁금한 거 물어보세요",
                    "examples": "고객 지원, 날씨 정보, 법률 상담, FAQ"
                },
                {
                    "id": "coupon_event",
                    "icon": "🎁",
                    "title": "쿠폰/이벤트",
                    "description": "혜택 받고 미션하고",
                    "examples": "쿠폰 발급, 출석 체크, 포인트 적립, 이벤트"
                },
                {
                    "id": "lesson_education",
                    "icon": "📚",
                    "title": "레슨/교육",
                    "description": "배우고 싶은 걸 찾아보세요",
                    "examples": "온라인 강의, 과외 예약, 학습 관리, 자격증"
                }
            ]
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 1 → Step 2: 서비스 카테고리 선택됨
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


    TEST_MODE = True  # True: 파일 읽기 모드, False: 정상 LLM 생성 모드
    TEST_JSON_PATH = r"F:\rooting\python\_google_gemini\chatbot\bot_designs\coupon_event\intermediate_step3.json"

    
    if user_msg.startswith("서비스선택:"):
        parts = user_msg.split(":", 2)
        category_id = parts[1]
        category_title = parts[2]
        
        print(f"[Step 1 완료] 선택: {category_id} - {category_title}")
        
        if session_key not in bot_creation_sessions:
            bot_creation_sessions[session_key] = {"stage": "step1", "data": {}}
        
        bot_creation_sessions[session_key]["data"]["category_id"] = category_id
        bot_creation_sessions[session_key]["data"]["category_title"] = category_title
        
        try:
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🧪 테스트 모드 분기
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if TEST_MODE:
                print(f"🧪 [TEST MODE] 파일에서 step3_json 로드: {TEST_JSON_PATH}")
                
                # 파일 읽기
                test_file = Path(TEST_JSON_PATH)
                
                if not test_file.exists():
                    raise FileNotFoundError(f"테스트 파일을 찾을 수 없습니다: {TEST_JSON_PATH}")
                
                with open(test_file, 'r', encoding='utf-8') as f:
                    step3_json = json.load(f)
                
                print(f"✅ [TEST MODE] step3_json 로드 완료: {len(step3_json)} keys")
                print(f"   - classification: {step3_json.get('classification', {}).keys()}")
                print(f"   - all_variables: {len(step3_json.get('all_variables', []))}개")
            
            else:
                print(f"🚀 [NORMAL MODE] LLM으로 step3_json 생성")
                
                # 정상 모드: LLM 호출
                pre_result = generate_complete_bot_design_pre(
                    room_id=room_id,
                    category_id=category_id, 
                    category_title=category_title,
                    user_description="자동차 발전기"
                )
                
                step3_json = pre_result.get("step3_json")
                print(f"step3_json: {step3_json}")
                
                if not step3_json:
                    return {
                        'error': 'generation_failed',
                        'reply': {'type': 'text', 'message': 'Step 3 생성 실패'},
                        'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                        'task_session_id': None,
                        'bot_changed': False,
                        'completed': False
                    }
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🔄 공통 처리: 서브봇 리스트 생성
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            subbot_list = []
            for subbot in step3_json.get("classification", {}).get("non_user_input_variables", []):
                subbot_list.append({
                    "variable_id": subbot.get("variable_id"),
                    "variable_name": subbot.get("variable_name"),
                    "sub_bot_id": subbot.get("sub_bot_id"),
                    "sub_bot_name": subbot.get("sub_bot_name"),
                    "api_endpoint": subbot.get("api_endpoint"),
                    "purpose": subbot.get("purpose"),
                    "trigger_keyword": subbot.get("trigger_keyword"),
                    "source": subbot.get("source"),
                    "why_not_ask_user": subbot.get("why_not_ask_user"),
                    "execution_logic": subbot.get("execution_logic"),
                    "data_type": None
                })
                
                # data_type 매칭
                for var in step3_json.get("all_variables", []):
                    if var.get("variable_name") == subbot.get("variable_name"):
                        subbot_list[-1]["data_type"] = var.get("data_type")
                        break
            
            print(f"📋 [Subbot List] {len(subbot_list)}개 서브봇 추출 완료")
            for idx, sb in enumerate(subbot_list, 1):
                print(f"   {idx}. {sb['sub_bot_name']} ({sb['sub_bot_id']})")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🎯 최종 봇 생성
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            final_result = generate_complete_bot_design(
                room_id=room_id,
                category_id=category_id,
                step3_json=step3_json,
                subbot_list=subbot_list,
                bot_db=bot_db,
                session_manager=session_manager 
            )
            
            response = {'type': 'text', 'message': '봇 생성이 완료되었습니다.'}
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
            
        except FileNotFoundError as e:
            print(f"❌ 테스트 파일 오류: {e}")
            
            response = create_text_response(f"❌ 테스트 파일을 찾을 수 없습니다.\n\n{str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            
            response = create_text_response(f"❌ JSON 파일 형식이 올바르지 않습니다.\n\n{str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
        
        except Exception as e:
            print(f"❌ 봇 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            
            response = create_text_response(f"❌ 봇 생성 중 오류가 발생했습니다.\n\n{str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 직접 설명 입력
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇설명:"):
        user_description = user_msg.split(":", 1)[1]
        print(f"[Step 1 완료] 직접 입력: {user_description}")
        
        if session_key not in bot_creation_sessions:
            bot_creation_sessions[session_key] = {"stage": "step1", "data": {}}
        
        bot_creation_sessions[session_key]["data"]["user_description"] = user_description
        
        try:
            design = generate_complete_bot_design(None, None, user_description)
            
            bot_creation_sessions[session_key]["data"]["design"] = design
            bot_creation_sessions[session_key]["data"]["selected_name"] = design["main_bot"]["name_suggestions"][0]
            bot_creation_sessions[session_key]["stage"] = "step2"
            
            response = {
                "type": "bot_management",
                "widget_type": "bot_creation_step2",
                "content": f"'{user_description}' 봇을 설계했습니다!",
                "design": design
            }
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
            
        except Exception as e:
            print(f"❌ LLM 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            
            response = create_text_response(f"❌ 봇 생성 중 오류가 발생했습니다.\n\n{str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 이름 선택
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇이름선택:"):
        selected_name = user_msg.split(":", 1)[1]
        bot_creation_sessions[session_key]["data"]["selected_name"] = selected_name
        
        response = create_text_response(f"✅ 봇 이름을 '{selected_name}'으로 선택했습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 메인봇 수정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg == "메인봇수정":
        bot_creation_sessions[session_key]["stage"] = "editing_main_bot"
        
        response = {
            "type": "bot_management",
            "widget_type": "text_input",
            "title": "✏️ 메인 봇 수정",
            "label": "메인 봇을 어떻게 수정할까요?",
            "placeholder": "예: 목적을 '할인 쿠폰 발급'으로 변경, 봇 이름 추가 제안",
            "help": "메인 봇의 이름, 목적, 전반적인 내용을 수정할 수 있습니다",
            "reply_prefix": "자유수정",
            "button_text": "수정"
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 서비스봇 추가
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg == "서비스봇추가":
        bot_creation_sessions[session_key]["stage"] = "adding_service_bot"
        
        response = {
            "type": "bot_management",
            "widget_type": "text_input",
            "title": "⚙️ 서비스 봇 추가",
            "label": "어떤 서비스 봇을 추가할까요?",
            "placeholder": "예: 사진 인증 봇, 결제 처리 봇, AI 추천 봇",
            "help": "서비스 봇이 할 일을 설명해주세요",
            "reply_prefix": "서비스봇추가설명",
            "button_text": "추가"
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 서비스봇 추가 설명
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("서비스봇추가설명:"):
        bot_description = user_msg.split(":", 1)[1]
        current_design = bot_creation_sessions[session_key]["data"]["design"]
        
        try:
            modification = f"'{bot_description}' 서비스 봇을 추가해줘"
            modified_design = apply_modification_with_llm(current_design, modification)
            
            bot_creation_sessions[session_key]["data"]["design"] = modified_design
            bot_creation_sessions[session_key]["stage"] = "step2"
            
            response = {
                "type": "bot_management",
                "widget_type": "bot_creation_step2",
                "content": f"✅ '{bot_description}' 서비스 봇이 추가되었습니다!",
                "design": modified_design
            }
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
            
        except Exception as e:
            print(f"❌ 서비스 봇 추가 오류: {e}")
            response = create_text_response(f"❌ 서비스 봇 추가 실패: {str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 서비스봇 삭제
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("서비스봇삭제:"):
        bot_id = user_msg.split(":", 1)[1]
        design = bot_creation_sessions[session_key]["data"]["design"]
        design["service_bots"] = [b for b in design["service_bots"] if b["bot_id"] != bot_id]
        
        response = {
            "type": "bot_management",
            "widget_type": "bot_creation_step2",
            "content": "서비스 봇이 삭제되었습니다.",
            "design": design
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 필드 추가
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg == "필드추가":
        bot_creation_sessions[session_key]["stage"] = "adding_field"
        
        response = {
            "type": "bot_management",
            "widget_type": "text_input",
            "title": "📊 필드 추가",
            "label": "어떤 정보를 수집할까요?",
            "placeholder": "예: 이메일 주소, 생년월일, 선호 카테고리",
            "help": "수집하고 싶은 정보를 자연스럽게 설명해주세요",
            "reply_prefix": "필드추가설명",
            "button_text": "추가"
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 필드 추가 설명
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("필드추가설명:"):
        field_description = user_msg.split(":", 1)[1]
        current_design = bot_creation_sessions[session_key]["data"]["design"]
        
        try:
            modification = f"'{field_description}' 필드를 추가해줘"
            modified_design = apply_modification_with_llm(current_design, modification)
            
            bot_creation_sessions[session_key]["data"]["design"] = modified_design
            bot_creation_sessions[session_key]["stage"] = "step2"
            
            response = {
                "type": "bot_management",
                "widget_type": "bot_creation_step2",
                "content": f"✅ '{field_description}' 필드가 추가되었습니다!",
                "design": modified_design
            }
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
            
        except Exception as e:
            print(f"❌ 필드 추가 오류: {e}")
            response = create_text_response(f"❌ 필드 추가 실패: {str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 필드 삭제
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("필드삭제:"):
        field_name = user_msg.split(":", 1)[1]
        design = bot_creation_sessions[session_key]["data"]["design"]
        design["main_bot"]["fields"] = [f for f in design["main_bot"]["fields"] if f["field_name"] != field_name]
        
        response = {
            "type": "bot_management",
            "widget_type": "bot_creation_step2",
            "content": "필드가 삭제되었습니다.",
            "design": design
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 자유 수정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("자유수정:"):
        modification_request = user_msg.split(":", 1)[1]
        
        if not modification_request.strip():
            response = create_text_response("수정 내용을 입력해주세요.")
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
        
        current_design = bot_creation_sessions[session_key]["data"]["design"]
        
        try:
            modified_design = apply_modification_with_llm(current_design, modification_request)
            bot_creation_sessions[session_key]["data"]["design"] = modified_design
            
            response = {
                "type": "bot_management",
                "widget_type": "bot_creation_step2",
                "content": f"✅ '{modification_request}' 수정이 완료되었습니다!",
                "design": modified_design
            }
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
            
        except Exception as e:
            print(f"❌ 수정 오류: {e}")
            import traceback
            traceback.print_exc()
            
            response = create_text_response(
                f"❌ 수정 중 오류가 발생했습니다.\n\n"
                f"요청: {modification_request}\n"
                f"오류: {str(e)}\n\n"
                f"다시 시도해주세요."
            )
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 생성 확정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg == "봇생성확정":
        design = bot_creation_sessions[session_key]["data"]["design"]
        selected_name = bot_creation_sessions[session_key]["data"]["selected_name"]
        
        main_bot_id = design["main_bot"]["bot_id"]
        
        definition = {
            "bot_id": main_bot_id,
            "bot_name": selected_name,
            "bot_type": "main",
            "goal": {
                "description": design["main_bot"]["goal"],
                "final_action": ""
            },
            "data_requirements": {
                "fields": design["main_bot"]["fields"]
            },
            "completion": {
                "conditions": {
                    "all_fields_collected": True
                },
                "webhook": {}
            }
        }
        
        definition_path = f'bots/main/{main_bot_id}.json'
        os.makedirs(os.path.dirname(definition_path), exist_ok=True)
        with open(definition_path, 'w', encoding='utf-8') as f:
            json.dump(definition, f, ensure_ascii=False, indent=2)
        
        success = bot_db.register_bot_file(
            bot_id=main_bot_id,
            bot_name=selected_name,
            bot_type='main',
            definition_file_path=definition_path,
            prompt_file_path=None,
            created_by='chat_ui'
        )
        
        if success:
            config_manager.load_from_database(bot_db)
            
            response = create_text_response(
                f"✅ '{selected_name}' 봇이 생성되었습니다!\n\n"
                f"🤖 메인 봇: {main_bot_id}\n"
                f"⚙️ 서비스 봇: {len(design['service_bots'])}개\n"
                f"📊 수집 필드: {len(design['main_bot']['fields'])}개"
            )
        else:
            response = create_text_response("❌ 봇 생성 실패")
        
        del bot_creation_sessions[session_key]
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': success
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 생성 완료 (폼 제출)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇생성완료:"):
        try:
            form_json = user_msg.split(":", 1)[1]
            form_data = json.loads(form_json)
            
            bot_id = form_data['bot_id']
            bot_name = form_data['bot_name']
            bot_type = form_data['bot_type']
            prompt = form_data.get('prompt', '')
            
            definition = {
                "bot_id": bot_id,
                "bot_name": bot_name,
                "bot_type": bot_type,
                "goal": {
                    "description": bot_name,
                    "final_action": ""
                },
                "data_requirements": {
                    "fields": []
                },
                "completion": {
                    "conditions": {},
                    "webhook": {}
                }
            }
            
            definition_path = f'bots/{bot_type}/{bot_id}.json'
            prompt_path = f'bots/prompts/{bot_id}_prompt.txt' if prompt else None
            
            os.makedirs(os.path.dirname(definition_path), exist_ok=True)
            with open(definition_path, 'w', encoding='utf-8') as f:
                json.dump(definition, f, ensure_ascii=False, indent=2)
            
            if prompt:
                os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
                with open(prompt_path, 'w', encoding='utf-8') as f:
                    f.write(prompt)
            
            success = bot_db.register_bot_file(
                bot_id=bot_id,
                bot_name=bot_name,
                bot_type=bot_type,
                definition_file_path=definition_path,
                prompt_file_path=prompt_path,
                created_by='chat_ui'
            )
            
            if success:
                config_manager.load_from_database(bot_db)
                response = create_text_response(f"✅ '{bot_name}' 봇이 생성되었습니다!")
            else:
                response = create_text_response(f"❌ 봇 생성 실패: 이미 존재하는 ID입니다.")
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': success
            }
            
        except Exception as e:
            print(f"봇 생성 오류: {e}")
            response = create_text_response(f"❌ 봇 생성 오류: {str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 편집
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇편집:"):
        bot_id = user_msg.split(":", 1)[1]
        bot_meta = bot_db.get_bot(bot_id)
        
        if not bot_meta:
            response = create_text_response(f"❌ 봇을 찾을 수 없습니다.")
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
        
        definition = bot_db.get_bot_definition(bot_id)
        prompt = bot_db.get_bot_prompt(bot_id) or ''
        
        available_service_bots = []
        if bot_meta['bot_type'] == 'main':
            available_service_bots = bot_db.get_all_bots(bot_type='service', active_only=True)
        
        callable_sub_bots = []
        if definition:
            if 'activation_conditions' in definition:
                mission_id = definition.get('activation_conditions', {}).get('mission_config_id')
                if mission_id:
                    callable_sub_bots.append(mission_id)
            elif 'data_requirements' in definition:
                for field in definition.get('data_requirements', {}).get('fields', []):
                    if field.get('acquisition_method') == 'service_bot':
                        service_id = field.get('acquisition_config', {}).get('service_bot_id')
                        if service_id and service_id not in callable_sub_bots:
                            callable_sub_bots.append(service_id)
        
        bot_data = {
            "bot_id": bot_meta['bot_id'],
            "bot_name": bot_meta['bot_name'],
            "bot_type": bot_meta['bot_type'],
            "is_active": bot_meta['is_active'] == 1,
            "prompt": prompt,
            "callable_sub_bots": callable_sub_bots
        }
        
        response = {
            "type": "bot_management",
            "widget_type": "bot_edit_form",
            "content": f"'{bot_meta['bot_name']}' 수정",
            "bot": bot_data,
            "definition": definition,
            "available_service_bots": [
                {
                    "bot_id": sb['bot_id'],
                    "bot_name": sb['bot_name']
                }
                for sb in available_service_bots
            ]
        }
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 수정 완료
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇수정완료:"):
        try:
            form_json = user_msg.split(":", 1)[1]
            update_data = json.loads(form_json)
            
            bot_id = update_data['bot_id']
            basic_info = update_data['basic_info']
            fields = update_data['fields']
            linked_services = update_data['linked_services']
            prompt = update_data['prompt']
            
            bot_meta = bot_db.get_bot(bot_id)
            if not bot_meta:
                response = create_text_response(f"❌ 봇을 찾을 수 없습니다.")
                
                return {
                    'reply': response,
                    'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                    'task_session_id': None,
                    'bot_changed': False,
                    'completed': False
                }
            
            definition = bot_db.get_bot_definition(bot_id)
            
            if 'data_schema' in definition:
                definition['data_schema'] = fields
            else:
                if 'data_requirements' not in definition:
                    definition['data_requirements'] = {}
                definition['data_requirements']['fields'] = fields
            
            if 'activation_conditions' in definition and linked_services:
                definition['activation_conditions']['mission_config_id'] = linked_services[0] if linked_services else None
            
            with open(bot_meta['definition_file_path'], 'w', encoding='utf-8') as f:
                json.dump(definition, f, ensure_ascii=False, indent=2)
            
            if prompt and bot_meta['prompt_file_path']:
                with open(bot_meta['prompt_file_path'], 'w', encoding='utf-8') as f:
                    f.write(prompt)
            
            bot_db.update_bot_metadata(
                bot_id,
                bot_name=basic_info['bot_name'],
                is_active=1 if basic_info['is_active'] else 0,
                field_count=len(fields)
            )
            
            config_manager.load_from_database(bot_db)
            
            response = create_text_response(f"✅ '{basic_info['bot_name']}' 봇이 수정되었습니다!")
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': True
            }
            
        except Exception as e:
            print(f"봇 수정 오류: {e}")
            import traceback
            traceback.print_exc()
            response = create_text_response(f"❌ 봇 수정 오류: {str(e)}")
            
            return {
                'error': str(e),
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 삭제 확인
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇삭제확인:"):
        bot_id = user_msg.split(":", 1)[1]
        bot_meta = bot_db.get_bot(bot_id)
        
        if bot_meta:
            response = create_confirm_dialog_response("삭제", bot_meta['bot_name'], bot_id)
        else:
            response = create_text_response(f"❌ 봇을 찾을 수 없습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 삭제 확인 완료
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("확인:삭제:"):
        bot_id = user_msg.split(":", 2)[2]
        bot_meta = bot_db.get_bot(bot_id)
        
        if bot_meta:
            bot_db.delete_bot(bot_id, soft=True)
            config_manager.load_from_database(bot_db)
            response = create_text_response(f"✅ '{bot_meta['bot_name']}' 봇이 삭제되었습니다.")
        else:
            response = create_text_response(f"❌ 봇을 찾을 수 없습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': bot_meta is not None
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 취소
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg == "취소":
        response = create_text_response("❌ 작업이 취소되었습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 봇 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("봇테스트:"):
        bot_id = user_msg.split(":", 1)[1]
        bot_meta = bot_db.get_bot(bot_id)
        
        if bot_meta:
            response = create_text_response(
                f"🧪 '{bot_meta['bot_name']}' 봇 테스트를 시작합니다.\n\n"
                f"이제 이 봇과 대화해보세요!"
            )
        else:
            response = create_text_response(f"❌ 봇을 찾을 수 없습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 방 목록
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg in ["방목록", "방 목록", "room list", "/rooms"]:
        rooms = bot_db.get_all_rooms()
        response = create_room_list_response(rooms)
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 방 선택 → 봇 할당 폼
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("방선택:"):
        room_id_selected = user_msg.split(":", 1)[1]
        room = bot_db.get_room(room_id_selected)
        
        if room:
            available_bots = bot_db.get_all_bots(bot_type='main', active_only=True)
            response = create_room_assign_form_response(room, available_bots)
        else:
            response = create_text_response(f"❌ 방을 찾을 수 없습니다.")
        
        return {
            'reply': response,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 방 봇 할당
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.startswith("방봇할당:"):
        parts = user_msg.split(":", 2)
        if len(parts) == 3:
            room_id_selected, bot_id = parts[1], parts[2]
            
            response = create_text_response(
                f"✅ 방 '{room_id_selected}'에 봇 '{bot_id}'가 할당되었습니다.\n"
                f"(업데이트 기능은 추후 구현 예정)"
            )
            
            return {
                'reply': response,
                'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
                'task_session_id': None,
                'bot_changed': False,
                'completed': False
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 테스트 모드
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg.strip() == "테스트":
        return {
            'reply': MOCK_DATA_BATCH,
            'bot_info': {'bot_id': 'system', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 자동 채우기 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if user_msg and user_msg.strip() == "자동":
        print(f"\n🤖 [Test Command] '자동' 감지")
        
        session, is_new = session_manager.get_or_create_session(room_id, member_id)
        current_bot_id = session.get_active_bot()
        result = auto_fill_test_data(session, current_bot_id, config_manager)
        
        session.conversation_history.append({
            "role": "user",
            "content": user_msg
        })
        
        session.conversation_history.append({
            "role": "assistant",
            "content": result['message']
        })
        
        bot_config = config_manager.get_bot_config(current_bot_id)
        
        return {
            'reply': result['message'],
            'bot_info': {
                'bot_id': current_bot_id,
                'bot_name': bot_config.bot_name if bot_config else current_bot_id,
                'bot_type': "메인봇" if len(session.bot_stack) == 1 else "서브봇"
            },
            'task_session_id': session.session_id,
            'auto_filled': True,
            'filled_count': result['filled_count'],
            'skipped_count': result['skipped_count'],
            'bot_changed': False,
            'completed': False
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 일반 대화 처리 (세션 매니저)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    try:
        session, is_new = session_manager.get_or_create_session(room_id, member_id)
        
        if extra_data:
            session.shared_context.update(extra_data)
        
        result = session_manager.handle_message(session, user_msg)

        # if result.get('skip'):
        #     print("⏭️ 메시지 무시됨 - 응답 전송하지 않음")

        #     return {
        #             "reply": "",  # ✅ 빈 문자열
        #             "skip": True,  # ✅ skip 플래그
        #             "bot_changed": False,
        #             "completed": False,
        #             "data_updated": False
        #         }


        
        current_bot_id = session.get_active_bot()
        bot_config = config_manager.get_bot_config(current_bot_id)
        
        bot_info = {
            'bot_id': current_bot_id,
            'bot_name': bot_config.bot_name if bot_config else current_bot_id,
            'bot_type': "메인봇" if len(session.bot_stack) == 1 else "서브봇"
        }
        
        # ✅ 순수 딕셔너리 반환 (jsonify 없음!)
        return {
            **result,
            'session': session,
            'bot_info': bot_info,
            'task_session_id': session.session_id
        }
        
    except Exception as e:
        print(f"❌ [process_user_message] 에러: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'error': str(e),
            'reply': {'type': 'text', 'message': '처리 중 오류가 발생했습니다.'},
            'bot_info': {'bot_id': 'unknown', 'bot_name': 'System', 'bot_type': '시스템'},
            'task_session_id': None,
            'bot_changed': False,
            'completed': False
        }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🆕 Step 4: 봇 관리 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/bots', methods=['GET'])
def get_bots():
    """
    봇 목록 조회
    
    Query params:
    - type: main | service (선택)
    - active: true | false (기본: true)
    """
    bot_type = request.args.get('type')
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    try:
        bots = bot_db.get_all_bots(bot_type=bot_type, active_only=active_only)
        
        # 메타데이터만 반환 (파일 내용 제외)
        result = []
        for bot in bots:
            result.append({
                'bot_id': bot['bot_id'],
                'bot_name': bot['bot_name'],
                'bot_type': bot['bot_type'],
                'version': bot['version'],
                'is_active': bot['is_active'] == 1,
                'goal_description': bot['goal_description'],
                'has_webhook': bot['has_webhook'] == 1,
                'field_count': bot['field_count'],
                'created_at': bot['created_at'],
                'updated_at': bot['updated_at']
            })
        
        return jsonify({
            'success': True,
            'count': len(result),
            'bots': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bots/<bot_id>', methods=['GET'])
def get_bot_detail(bot_id):
    """
    봇 상세 조회 (전체 JSON 포함)
    """
    try:
        # 1. 메타데이터
        bot_meta = bot_db.get_bot(bot_id)
        if not bot_meta:
            return jsonify({
                'success': False,
                'error': f"Bot '{bot_id}' not found"
            }), 404
        
        # 2. 전체 정의
        bot_definition = bot_db.get_bot_definition(bot_id)
        
        # 3. 프롬프트
        bot_prompt = bot_db.get_bot_prompt(bot_id)
        
        return jsonify({
            'success': True,
            'bot': {
                'bot_id': bot_meta['bot_id'],
                'bot_name': bot_meta['bot_name'],
                'bot_type': bot_meta['bot_type'],
                'version': bot_meta['version'],
                'is_active': bot_meta['is_active'] == 1,
                'definition': bot_definition,
                'prompt': bot_prompt,
                'file_paths': {
                    'definition': bot_meta['definition_file_path'],
                    'prompt': bot_meta['prompt_file_path']
                },
                'created_at': bot_meta['created_at'],
                'updated_at': bot_meta['updated_at']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bots', methods=['POST'])
def create_bot():
    """
    봇 생성
    
    Request Body:
    {
        "bot_id": "new_bot",
        "bot_name": "새 봇",
        "bot_type": "main",
        "definition": { 봇 정의 JSON },
        "prompt": "프롬프트 내용"
    }
    """
    try:
        data = request.json
        
        # 필수 필드 검증
        required_fields = ['bot_id', 'bot_name', 'bot_type', 'definition']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f"Missing required field: {field}"
                }), 400
        
        bot_id = data['bot_id']
        bot_name = data['bot_name']
        bot_type = data['bot_type']
        definition = data['definition']
        prompt = data.get('prompt', '')
        
        # bot_type 검증
        if bot_type not in ['main', 'service']:
            return jsonify({
                'success': False,
                'error': "bot_type must be 'main' or 'service'"
            }), 400
        
        # 이미 존재하는지 확인
        if bot_db.get_bot(bot_id):
            return jsonify({
                'success': False,
                'error': f"Bot '{bot_id}' already exists"
            }), 409
        
        # 파일 경로 설정
        definition_path = f'bots/{bot_type}/{bot_id}.json'
        prompt_path = f'bots/prompts/{bot_id}_prompt.txt' if prompt else None
        
        # 1. JSON 파일 저장
        os.makedirs(os.path.dirname(definition_path), exist_ok=True)
        with open(definition_path, 'w', encoding='utf-8') as f:
            json.dump(definition, f, ensure_ascii=False, indent=2)
        
        # 2. 프롬프트 파일 저장
        if prompt:
            os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
        
        # 3. DB 등록
        success = bot_db.register_bot_file(
            bot_id=bot_id,
            bot_name=bot_name,
            bot_type=bot_type,
            definition_file_path=definition_path,
            prompt_file_path=prompt_path,
            created_by='api'
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to register bot in database'
            }), 500
        
        # 4. ConfigManager 리로드
        config_manager.load_from_database(bot_db)
        
        return jsonify({
            'success': True,
            'message': f"Bot '{bot_id}' created successfully",
            'bot_id': bot_id
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bots/<bot_id>', methods=['PUT'])
def update_bot(bot_id):
    """
    봇 수정
    
    Request Body:
    {
        "bot_name": "수정된 이름" (선택),
        "definition": { 수정된 정의 } (선택),
        "prompt": "수정된 프롬프트" (선택),
        "is_active": true/false (선택)
    }
    """
    try:
        # 봇 존재 확인
        bot_meta = bot_db.get_bot(bot_id)
        if not bot_meta:
            return jsonify({
                'success': False,
                'error': f"Bot '{bot_id}' not found"
            }), 404
        
        data = request.json
        
        # 1. 정의 파일 수정
        if 'definition' in data:
            with open(bot_meta['definition_file_path'], 'w', encoding='utf-8') as f:
                json.dump(data['definition'], f, ensure_ascii=False, indent=2)
        
        # 2. 프롬프트 수정
        if 'prompt' in data and bot_meta['prompt_file_path']:
            with open(bot_meta['prompt_file_path'], 'w', encoding='utf-8') as f:
                f.write(data['prompt'])
        
        # 3. 메타데이터 수정
        update_fields = {}
        if 'bot_name' in data:
            update_fields['bot_name'] = data['bot_name']
        if 'is_active' in data:
            update_fields['is_active'] = 1 if data['is_active'] else 0
        
        if update_fields:
            bot_db.update_bot_metadata(bot_id, **update_fields)
        
        # 4. ConfigManager 리로드
        config_manager.load_from_database(bot_db)
        
        return jsonify({
            'success': True,
            'message': f"Bot '{bot_id}' updated successfully"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bots/<bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """
    봇 삭제 (soft delete)
    
    Query params:
    - hard: true (완전 삭제)
    """
    try:
        hard_delete = request.args.get('hard', 'false').lower() == 'true'
        
        # 봇 존재 확인
        bot_meta = bot_db.get_bot(bot_id)
        if not bot_meta:
            return jsonify({
                'success': False,
                'error': f"Bot '{bot_id}' not found"
            }), 404
        
        # 삭제
        bot_db.delete_bot(bot_id, soft=not hard_delete)
        
        # ConfigManager 리로드
        config_manager.load_from_database(bot_db)
        
        return jsonify({
            'success': True,
            'message': f"Bot '{bot_id}' {'deleted' if hard_delete else 'deactivated'}"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bots/validate', methods=['POST'])
def validate_bot():
    """
    봇 정의 검증
    
    Request Body:
    {
        "definition": { 봇 정의 JSON }
    }
    """
    try:
        data = request.json
        definition = data.get('definition')
        
        if not definition:
            return jsonify({
                'success': False,
                'error': 'Missing definition'
            }), 400
        
        errors = []
        warnings = []
        
        # 기본 필드 검증
        if 'bot_id' not in definition:
            errors.append("Missing required field: bot_id")
        
        if 'bot_name' not in definition:
            errors.append("Missing required field: bot_name")
        
        # data_requirements 검증
        if 'data_requirements' in definition:
            fields = definition['data_requirements'].get('fields', [])
            if not fields:
                warnings.append("No data fields defined")
        
        return jsonify({
            'success': len(errors) == 0,
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 방 관리 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """방 목록 조회"""
    try:
        rooms = bot_db.get_all_rooms()
        return jsonify({
            'success': True,
            'count': len(rooms),
            'rooms': rooms
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rooms/<room_id>/assign-bot', methods=['POST'])
def assign_bot_to_room(room_id):
    """
    방에 메인 봇 할당
    
    Request Body:
    {
        "main_bot_id": "coupon_issue_task"
    }
    """
    try:
        data = request.json
        main_bot_id = data.get('main_bot_id')
        
        if not main_bot_id:
            return jsonify({
                'success': False,
                'error': 'Missing main_bot_id'
            }), 400
        
        # 봇 존재 확인
        if not bot_db.get_bot(main_bot_id):
            return jsonify({
                'success': False,
                'error': f"Bot '{main_bot_id}' not found"
            }), 404
        
        # 방이 이미 있으면 업데이트, 없으면 생성
        existing_room = bot_db.get_room(room_id)
        
        if existing_room:
            # 업데이트 로직 (DB에 update_room 메서드 필요)
            return jsonify({
                'success': False,
                'error': 'Room update not implemented yet'
            }), 501
        else:
            # 새로 생성
            bot_db.create_room(room_id, f"Room {room_id}", main_bot_id)
        
        # ConfigManager 리로드
        config_manager.load_from_database(bot_db)
        
        return jsonify({
            'success': True,
            'message': f"Bot '{main_bot_id}' assigned to room '{room_id}'"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 시스템 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/system/reload', methods=['POST'])
def reload_system():
    """ConfigManager 강제 리로드"""
    try:
        config_manager.load_from_database(bot_db)
        
        return jsonify({
            'success': True,
            'message': 'System reloaded',
            'bots_count': len(config_manager.bots),
            'rooms_count': len(config_manager.rooms)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 기존 /task_chat 엔드포인트는 그대로 유지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def send_to_user(room_id: str, user_id: str, event: str, data: dict) -> bool:
    """
    특정 user에게 WebSocket 메시지 전송
    
    Returns:
        성공 여부
    """
    if room_id in room_users and user_id in room_users[room_id]:
        sid = room_users[room_id][user_id]
        
      
        socketio.emit(event, data, to=sid)
        
        print(f"📤 [WebSocket] {event} → {user_id} (room: {room_id})")
        return True
    else:
        print(f"⚠️ [WebSocket] 연결 없음: user={user_id}, room={room_id}")
        return False


@socketio.on('connect')
def handle_connect():
    print(f"🔌 연결: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"🔌 연결 해제: {request.sid}")

@socketio.on('join')
def handle_join(data):
    room_id = data['room_id']
    user_id = data['user_id']
    
    join_room(room_id)
    
    if room_id not in room_users:
        room_users[room_id] = {}
    
    room_users[room_id][user_id] = request.sid
    
    print(f"✅ {user_id} joined {room_id}")
    
    emit('joined', {'status': 'success', 'room_id': room_id})



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. HTTP 엔드포인트 (얇은 래퍼)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/task_chat', methods=['POST'])
def task_chat():
    """HTTP API 엔드포인트"""
    data = request.json
    user_msg = data.get('message', '')
    room_id = str(data.get('room_id', ''))
    member_id = data.get('member_id', '')
    
    print(f"\n[HTTP 명령어] {user_msg}")
    
    # 입력 검증
    if not room_id or not member_id:
        return jsonify({"error": "room_id, member_id 필수"}), 400
    
    # 핵심 로직 호출
    result = process_user_message(room_id, member_id, user_msg, data)
    
    # 에러 처리
    if 'error' in result:
        return jsonify({
            "error": result['error'],
            "message": result['reply'].get('message', '오류가 발생했습니다.')
        }), 500
    
    # HTTP 응답 (session 객체 제외)
    return jsonify({
        "reply": result['reply'],
        "task_session_id": result['task_session_id'],
        "bot_changed": result.get('bot_changed', False),
        "completed": result.get('completed', False),
        "bot_info": result['bot_info']
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. WebSocket 핸들러 (얇은 래퍼)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━




@socketio.on('send_message')
def handle_websocket_message(data):
    """WebSocket 메시지 처리"""
    try:
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        user_message = data.get('message')
        
        print(f"\n{'='*60}")
        print(f"📨 [WebSocket M0000essage]")
        print(f"   Room: {room_id}")
        print(f"   User: {user_id}")
        print(f"   Message: {user_message}")
        print(f"{'='*60}\n")
        
        # 입력 검증
        if not room_id or not user_id:
            emit('error', {
                'error': 'missing_parameters',
                'message': 'room_id와 user_id는 필수입니다.'
            })
            return
        
        # ✅ 핵심 로직 호출 (한 번만!)



        result = process_user_message(room_id, user_id, user_message,data)


        if result.get('skip'):
            print("⏭️ 메시지 무시됨 - 응답 전송하지 않음")
            return



       
        
        # 에러 체크
        if 'error' in result:
            emit('error', {
                'error': result['error'],
                'message': result['reply'].get('message', '오류가 발생했습니다.')
            })
            return
        
        # reply 데이터 파싱
        reply_data = result.get('reply')
        
        # JSON 문자열이면 파싱
        if isinstance(reply_data, str):
            try:
                reply_data = json.loads(reply_data)
            except json.JSONDecodeError:
                # 파싱 실패 시 텍스트로 처리
                reply_data = {
                    'type': 'text',
                    'message': reply_data
                }
        
        # ✅ WebSocket 전송 (봇 정보 포함)
        bot_info = result['bot_info']
        
        if isinstance(reply_data, dict):
            emit('bot_reply', {
                **reply_data,
                'bot_id': bot_info['bot_id'],
                'bot_name': bot_info['bot_name'],
                'bot_type': bot_info['bot_type']
            })
        else:
            emit('bot_reply', {
                'type': 'text',
                'message': str(reply_data),
                'bot_id': bot_info['bot_id'],
                'bot_name': bot_info['bot_name'],
                'bot_type': bot_info['bot_type']
            })
        
        print(f"✅ [WebSocket] 응답 전송 완료 ({bot_info['bot_type']}: {bot_info['bot_name']})\n")
        
    except Exception as e:
        print(f"❌ [WebSocket] 에러: {e}")
        import traceback
        traceback.print_exc()
        
        emit('error', {
            'error': str(e),
            'message': '처리 중 오류가 발생했습니다.'
        })
if __name__ == "__main__":
   # config_manager.load_from_files()
    # 🆕 DB 초기화

    # global bot_db


    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🗄️  SQLite DB 초기화 중...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    bot_db = BotDatabase(db_path="bots.db")
    bot_db.test_connection()
    bot_db.get_table_info()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")



    config_manager.load_from_database(bot_db)

    # ✅ 로드 검증
    print("\n=== 로드된 Bot 목록 ===")
    for bot_id, bot_config in config_manager.bots.items():
        prompt_len = len(bot_config.prompt_template)
        status = "✅" if prompt_len > 0 else "❌"
        print(f"{status} {bot_id}: {prompt_len} chars")
    
    print("\n=== 로드된 Prompt 템플릿 ===")
    for prompt_id, prompt_data in config_manager.prompt_templates.items():
        template_len = len(prompt_data['template'])
        print(f"📝 {prompt_id}: {template_len} chars")




    
    session_manager = SessionManager(config_manager)
    # app.run(host='0.0.0.0', port=5000, debug=True)


    socketio.run(app, host='0.0.0.0', port=5000, debug=True)