# 봇 작업 위임 중복 실행 문제 분석 및 해결 방안

## 📋 문제 상황

### 현재 플로우
1. **메인봇**: 다음에 채울 필드 계산 → `phone_verification` (서브봇 필드)
2. **사용자 입력 수집**: 사용자가 전화번호 입력
3. **서브봇 호출**: `call_subbot` 액션 실행 → `push_bot('phone_verifier')`
4. **서브봇 작업**: 전화번호 인증 수행 → 데이터 저장 (`phone_verified = true`)
5. **서브봇 완료**: `complete_task` 액션 실행 → `pop_bot()` → 메인봇 복귀
6. **❌ 문제 발생**: 메인봇이 `build_xml_system_prompt()` 재호출 시, `phone_verification` 필드를 다시 "현재 필드"로 인식
7. **무한 루프**: 서브봇을 다시 호출하려고 시도

### 근본 원인

#### 코드 위치: `ragmanager.py:3503-3539`
현재 필드 찾기 로직:
```python
for i, field_item in enumerate(all_fields_in_order):
    field_name = field_item['field_name']
    value = current_data.get(field_name)
    is_empty = value is None or (isinstance(value, str) and not value.strip())

    if is_empty:
        if current_field_name is None:
            current_field_name = field_name  # ❌ 서브봇 필드도 현재 필드로 설정됨
```

**문제점**:
- 서브봇이 완료되어도, 메인 데이터 스키마의 서브봇 필드(`phone_verification`)는 여전히 비어있을 수 있음
- 서브봇은 자신의 내부 필드만 채우고(`phone_verified` 등), 메인봇의 서브봇 필드는 채우지 않음
- 메인봇 복귀 후, 다시 같은 서브봇 필드를 "현재 필드"로 인식하여 재호출 시도

#### 코드 위치: `ragmanager.py:3610-3633`
```python
is_current_subbot = 'sub_bot_id' in current_var

if is_current_subbot:
    # ❌ 이미 실행된 서브봇인지 체크하지 않음!
    return self._generate_new_bot_initial_message(
        session=session,
        new_bot_id=sub_bot_id,
        transition_message="🤖 서브봇 시작!"
    )
```

---

## ✅ 해결 방안

### 방안 1: 세션 메타데이터에 서브봇 실행 이력 추적 (권장)

#### 장점
- 명확한 실행 이력 관리
- 디버깅 용이
- 서브봇 필드가 비어있어도 재호출 방지

#### 구현 단계

##### 1) 세션에 메타데이터 추가 (이미 구현되어 있으면 스킵)
```python
class SessionStateManager:
    def __init__(self, ...):
        # ...
        self.metadata = {}  # 추가

    def get_metadata(self, key, default=None):
        return self.metadata.get(key, default)

    def set_metadata(self, key, value):
        self.metadata[key] = value
```

##### 2) 서브봇 호출 시 이력 기록
**위치**: `ragmanager.py:1116-1135` (`_handle_call_subbot`)

```python
def _handle_call_subbot(self, action, session, result):
    """서브봇 호출 처리"""
    subbot_id = action.data.get('subbot_id')

    if not subbot_id:
        print(f"   ⚠️ subbot_id 없음")
        return

    print(f"   🔄 서브봇 전환: {session.get_active_bot()} → {subbot_id}")

    # ✅ 서브봇 실행 이력 기록 (추가!)
    executed_subbots = session.get_metadata('executed_subbots', {})
    current_bot = session.get_active_bot()

    # 현재 처리 중인 필드 찾기 (필요 시)
    # 예: action.data에서 추출하거나 session.current_processing_field 사용
    # 여기서는 subbot_id만 기록 (간단한 방법)
    executed_subbots[subbot_id] = {
        'called_from': current_bot,
        'timestamp': datetime.utcnow().isoformat()
    }
    session.set_metadata('executed_subbots', executed_subbots)
    print(f"   📝 서브봇 실행 이력 기록: {subbot_id}")

    # ✅ 즉시 전환
    session.push_bot(subbot_id)
    # ...
```

##### 3) 현재 필드가 서브봇일 때 실행 이력 확인
**위치**: `ragmanager.py:3610-3633` (`build_xml_system_prompt`)

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6️⃣ 현재 필드 타입 검증
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("-" * 80)
print("6️⃣ 현재 필드 타입 검증")
print("-" * 80)

is_current_subbot = 'sub_bot_id' in current_var
print(f"🔍 현재 필드 타입: {'서브봇 ❌' if is_current_subbot else 'user_input ✅'}")

if is_current_subbot:
    sub_bot_id = current_var.get('sub_bot_id', '')

    # ✅✅✅ 서브봇 실행 이력 확인 (추가!)
    executed_subbots = session.get_metadata('executed_subbots', {})

    if sub_bot_id in executed_subbots:
        print(f"⏭️  서브봇 이미 실행됨: {sub_bot_id}")
        print(f"   실행 시각: {executed_subbots[sub_bot_id].get('timestamp', 'N/A')}")
        print(f"   호출자: {executed_subbots[sub_bot_id].get('called_from', 'N/A')}")
        print(f"   ➡️  다음 필드로 건너뛰기")

        # 다음 필드로 이동하거나, 완료 처리
        # 옵션 1: 다음 빈 필드를 current_field_name으로 설정하고 아래 로직 계속
        # 옵션 2: 직접 다음 필드 처리 프롬프트 생성

        # 여기서는 옵션 1 구현: next_field_name이 있으면 그것을 current로 설정
        if next_field_name:
            print(f"   📌 다음 필드를 현재 필드로 재설정: {next_field_name}")
            current_field_name = next_field_name
            current_var = next_var

            # 다시 서브봇인지 체크 (재귀적으로)
            # 간단하게는: 서브봇 아닌 필드를 찾을 때까지 반복
            # 하지만 여기서는 간단히 처리
            is_current_subbot = 'sub_bot_id' in current_var if current_var else False

            # 다음 필드도 서브봇이면? 재귀 처리 필요
            # 일단 user_input 필드라고 가정하고 계속 진행
            if not is_current_subbot:
                # 정상적으로 user_input 필드 처리로 진행
                pass
            else:
                # 다음 필드도 서브봇! 추가 처리 필요
                logger.warning(f"⚠️  연속된 서브봇 필드 감지: {next_field_name}")
                # TODO: 다음 서브봇도 이미 실행되었는지 체크
        else:
            # 다음 필드 없음 → 모든 필드 완료
            print(f"   ✅ 모든 필드 완료!")
            return _build_final_completion_prompt(bot_config, current_data)

    else:
        # 서브봇이 아직 실행되지 않았음 → 정상적으로 서브봇 시작
        print(f"🤖 서브봇 시작!")
        print(f"   필드명: {current_field_name}")
        print(f"   서브봇 ID: {sub_bot_id}")

        sub_bot_config = config_manager.get_bot_config(sub_bot_id)

        if not sub_bot_config:
            logger.error(f"❌ 서브봇 설정을 찾을 수 없음: {sub_bot_id}")
            return f"ERROR: 서브봇 설정을 찾을 수 없습니다: {sub_bot_id}"

        print(f"✅ 서브봇 설정 로드 완료: {sub_bot_config.task_name}")

        # ✅ 서브봇 초기 메시지 생성
        return self._generate_new_bot_initial_message(
            session=session,
            new_bot_id=sub_bot_id,
            transition_message="🤖 서브봇 시작!"
        )

# ✅ 여기부터는 user_input 필드 처리 (기존 로직)
if not is_current_subbot:
    # 7️⃣ 현재 step 안내 (기존 코드)
    # ...
```

##### 4) 서브봇 완료 시 이력 정리 (선택사항)
**위치**: `ragmanager.py:1034-1055` (`_handle_complete_task`)

```python
def _handle_complete_task(self, action, session, result, config_manager):
    """작업 완료 처리"""
    bot_config = config_manager.get_bot_config(session.get_active_bot())

    # ... 기존 완료 체크 로직 ...

    if bot_config.is_subbot:
        # 서브봇 완료
        print(f"   ✅ 서브봇 완료: {bot_config.bot_id}")
        result['completed'] = True
        result['bot_changed'] = True
        result['target_bot_id'] = session.pop_bot()

        # ✅ 완료 시점을 메타데이터에 추가 기록 (선택사항)
        executed_subbots = session.get_metadata('executed_subbots', {})
        if bot_config.bot_id in executed_subbots:
            executed_subbots[bot_config.bot_id]['completed_at'] = datetime.utcnow().isoformat()
            session.set_metadata('executed_subbots', executed_subbots)

        print(f"   🔄 복귀 대상: {result['target_bot_id']}")
    else:
        # 메인봇 완료
        # ...
```

---

### 방안 2: 서브봇 필드에 마커 값 저장

#### 개념
서브봇이 완료되면, 메인 데이터 스키마의 서브봇 필드에 특수 마커 값(`"__COMPLETED__"` 등)을 저장

#### 구현
```python
# _handle_complete_task에서
if bot_config.is_subbot:
    # 서브봇이 처리한 필드 이름 찾기
    # (이를 위해 서브봇 호출 시 처리 중인 필드를 세션에 저장해야 함)
    processing_field = session.get_metadata('current_subbot_field')

    if processing_field:
        session.shared_context[processing_field] = "__SUBBOT_COMPLETED__"
        print(f"   ✅ 서브봇 필드 마커 저장: {processing_field}")
```

#### 단점
- 데이터 오염 가능성
- 추가적인 필터링 로직 필요
- 디버깅 복잡

---

### 방안 3: 현재 필드 찾기 로직 개선

#### 개념
"현재 필드 찾기" 단계에서 이미 서브봇 필드를 건너뛰기

#### 구현
**위치**: `ragmanager.py:3503-3539`

```python
# ✅ 현재 필드와 다음 필드 찾기
current_field_name = None
# ...

executed_subbots = session.get_metadata('executed_subbots', {})

for i, field_item in enumerate(all_fields_in_order):
    field_name = field_item['field_name']
    value = current_data.get(field_name)
    is_empty = value is None or (isinstance(value, str) and not value.strip())

    print(f"🔍 [{i}] {field_item['step_key']}.{field_name}: value={value}, is_empty={is_empty}")

    if is_empty:
        # ✅ 서브봇 필드인지 확인
        field_var = _find_field_in_schema(field_name, data_schema)
        is_subbot_field = field_var and 'sub_bot_id' in field_var

        if is_subbot_field:
            sub_bot_id = field_var.get('sub_bot_id', '')
            if sub_bot_id in executed_subbots:
                print(f"   ⏭️  서브봇 필드 스킵 (이미 실행됨): {field_name}")
                continue  # 다음 필드로

        if current_field_name is None:
            # ✅ 비어있고, 실행되지 않은 첫 번째 필드
            current_field_name = field_name
            current_field_step = field_item['step_key']
            current_field_index = i
            print(f"   ✅ 현재 필드로 설정: {current_field_step}.{field_name}")

            # 다음 필드 찾기 로직...
            break
```

#### 장점
- 현재 필드 선택 단계에서 문제 차단
- 6️⃣ 단계에서 추가 체크 불필요

#### 단점
- `_find_field_in_schema` 반복 호출로 성능 저하 가능

---

## 🎯 권장 해결 방안

**방안 1 + 방안 3 조합**

1. **서브봇 호출 시**: `_handle_call_subbot`에서 실행 이력 기록
2. **현재 필드 찾기 시**: 실행 이력을 확인하여 이미 실행된 서브봇 필드 스킵
3. **6️⃣ 검증 단계**: 추가 안전장치로 이력 재확인

---

## 📝 테스트 시나리오

### 정상 플로우
1. 메인봇: `name` (user_input) 수집 → 완료
2. 메인봇: `phone` (user_input) 수집 → 완료
3. 메인봇: `phone_verification` (서브봇) → 서브봇 호출
4. 서브봇: 인증 작업 수행 → `complete_task`
5. 메인봇 복귀: `address` (user_input) 수집 ✅

### 수정 전 문제 플로우
1~4. 동일
5. 메인봇 복귀: `phone_verification` 다시 감지 → 서브봇 재호출 ❌

### 수정 후 플로우
1~4. 동일
5. 메인봇 복귀:
   - `phone_verification` 체크 → 실행 이력 확인 → 스킵
   - `address`를 현재 필드로 설정 → 정상 진행 ✅

---

## 🚀 구현 우선순위

1. ✅ **세션 메타데이터 구조 확인/추가** (`get_metadata`, `set_metadata`)
2. ✅ **서브봇 호출 시 이력 기록** (`_handle_call_subbot` 수정)
3. ✅ **현재 필드 찾기 로직 개선** (3503-3539 라인)
4. ✅ **6️⃣ 검증 단계 안전장치 추가** (3610-3633 라인)
5. ⚠️ **테스트**: 서브봇 → 복귀 → 다음 필드 정상 진행 확인

---

## 🐛 추가 고려사항

### 서브봇 실행 이력 초기화
- 세션 종료 시: 자동 삭제 (세션 객체와 함께 사라짐)
- 메인봇 재시작 시: 이력 유지 여부 결정 필요
- 같은 서브봇 재실행 허용 여부: 설정 옵션 고려

### 연속된 서브봇 필드
만약 workflow가 다음과 같다면:
```
step1: [name, phone]
step2: [phone_verification (서브봇)]
step3: [address_verification (서브봇)]
step4: [payment]
```

서브봇 A 완료 → 복귀 → 서브봇 B 즉시 호출

이 경우 사용자 입력 없이 서브봇 체인 실행을 지원해야 함.

**해결**:
- 메인봇 복귀 후, 다음 필드가 서브봇이면 자동 호출
- 또는 서브봇 완료 시 다음 필드 체크 → 서브봇이면 즉시 호출

---

## 📚 참고 코드 위치

- 세션 관리: `ragmanager.py:3049-3137` (`SessionStateManager`)
- 서브봇 호출: `ragmanager.py:1116-1135` (`_handle_call_subbot`)
- 서브봇 완료: `ragmanager.py:1034-1055` (`_handle_complete_task`)
- 현재 필드 찾기: `ragmanager.py:3503-3539`
- 서브봇 체크: `ragmanager.py:3610-3633`
- 봇 스택 관리: `ragmanager.py:3103-3136` (`get_active_bot`, `push_bot`, `pop_bot`)
