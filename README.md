# MasterClause - Music Contract Analyzer (v2)

음악 아티스트 · 엔터테인먼트 변호사 · 음반사를 위한 **데스크탑 앱** (Windows · macOS).
계약서(PDF/DOCX)를 올리고 옵션을 확정하면, AI 관련 위험 조항을 자동 탐지하고
위험도 · 산업 표준 비교 · 관할별 법리 · 협상 전략을 담은 리포트를 지정 경로에
저장합니다. 순수 네이티브 GUI(PySide6/Qt), 인프로세스 호출, 외부 통신은
Anthropic API 하나뿐입니다.

> 본 구현은 `DEVELOPMENT_PLAN_v2.md`를 따릅니다.

---

## 핵심 기능

- **입력**: PDF/DOCX 업로드(드래그앤드롭 지원) + 리포트 저장 경로 지정
- **분석 직전 3대 옵션**
  - 입장(Perspective): 엔터테인먼트 변호사 / 아티스트 / 음반사 — *누구 입장에서의 위험인가*
  - 출력 언어(Output Language): 한글 / 영문 (조항 원문은 원본 언어로 보존)
  - 관할(Jurisdiction): 대한민국 / 미국(주: CA/NY/TN/DC/그 외)
- **AI 조항 분석**: 9종 AIIssueType 탐지, 원문(verbatim) 보존, 집행가능성·법적 근거
- **입장별 위험 평가**: 같은 조항도 입장에 따라 RED/YELLOW/GREEN 이 달라짐
- **관할별 법리 노트** + 준거법↔관할 충돌 탐지
- **산업 표준 벤치마크**(FAVORABLE/NEUTRAL/UNFAVORABLE)
- **협상 플레이북**(MUST_FIX·walk-away 우선 정렬)
- **사용자 우려 맞춤 조언**: "가장 큰 우려"를 입력하면, 산출된 분석에 근거해 그 우려에
  직접 답하는 조언을 추가 생성 (근거 없는 날조 방지)
- **리포트 출력**: DOCX 기본(Times New Roman, 단색, 법무 메모 스타일), PDF 선택

---

## 빠른 시작

```powershell
# 1) 가상환경 + 의존성
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 2) 실행
python run.py
#   또는
python -m app.main
```

첫 실행 시 **설정 화면**에서 Anthropic API 키를 입력하고 [연결 테스트] → [저장]
하세요. 키는 Windows 자격 증명 관리자(keyring)에 저장되며 화면에 평문으로 다시
노출되지 않습니다.

### 사용 흐름
1. **파일 선택 + 저장 경로 지정** → 다음
2. **옵션 확정**(입장 / 언어 / 관할·주 / 프라이버시 / 우려) → 분석 시작
3. **진행**(파싱 → AI 분석 → 관할/벤치마크 → 리포트, 취소 가능)
4. **결과** 요약 + 우려 조언 + 조항 리스트 + 플레이북 + 저장 안내(폴더/리포트 열기)

---

## 아키텍처 (단일 프로세스)

```
UI (PySide6, QStackedWidget) ──▶ QThread Worker ──▶ Core (인프로세스)
                                                     parser → privacy → analyzer(Claude)
                                                     → jurisdiction → benchmarks → playbook
                                                     → report_writer → 지정 경로 저장
                              keyring(API 키) · (선택)SQLite 이력 · Anthropic API
```

### 프로젝트 구조
```
00_music_contract_analyzer/
├─ run.py                     # 진입 런처 (PyInstaller/개발 공용)
├─ config.py                  # 경로·모델명·기본값 (단일 관리)
├─ requirements.txt
├─ app/
│  ├─ main.py                 # QApplication + 테마
│  ├─ state.py                # 앱 상태 + 설정 저장(config.json, 키 제외)
│  ├─ worker.py               # QThread 분석 워커 (진행/취소)
│  └─ ui/
│     ├─ main_window.py       # 화면 전환 + 워커 수명주기
│     ├─ screen_upload.py     # 1단계
│     ├─ screen_options.py    # 2단계 (입장/언어/관할/우려)
│     ├─ screen_progress.py   # 3단계
│     ├─ screen_result.py     # 4단계
│     ├─ screen_settings.py   # API 키 + 기본 옵션
│     └─ widgets.py           # ScoreCard, RiskBadge, ClauseItem 등
├─ core/
│  ├─ models.py               # Pydantic 도메인 모델 (단일 진실 공급원)
│  ├─ parser.py               # PDF/DOCX → 정규화 텍스트
│  ├─ privacy.py              # 가역 익명화 / zero-retention
│  ├─ api_key.py              # keyring 저장 + 키 검증
│  ├─ prompts.py              # 입장/언어/관할 프롬프트 구성
│  ├─ analyzer.py             # Claude 호출 + 스키마 강제/재시도
│  ├─ jurisdiction.py         # KR/US-주 법리 매핑
│  ├─ benchmarks.py           # 유형별 산업 표준
│  ├─ playbook.py             # 협상 항목 정렬
│  └─ report_writer.py        # DOCX/PDF 생성
├─ data/
│  ├─ jurisdiction/*.json     # 관할별 법리(검수 대상 초안)
│  └─ benchmarks/*.json       # 유형별 표준
├─ tests/                     # pytest (네트워크 불필요)
└─ build/                     # PyInstaller spec + Inno Setup + 빌드 노트
```

---

## 모델 / 비용

- 기본 모델: `claude-opus-4-8` (정밀). 비용 우선 시 설정에서 `claude-haiku-4-5`로 전환.
- 모델 문자열·기본값은 `config.py`에서 관리합니다.
- 시스템 프롬프트는 prompt caching 으로 캐시되어 비용·지연을 절감합니다.

---

## 프라이버시 / 보안

- **로컬 우선**: 파일 처리는 로컬에서. 외부 통신은 Anthropic API 호출뿐.
- **API 키**: GUI 입력 → keyring(Windows 자격 증명 관리자) 저장. config.json 에 미저장.
- **익명화(선택)**: 전송 전 이메일·전화·주민/SSN 등 식별정보를 가역 마스킹하고,
  결과의 원문 인용에 실제 값을 복원합니다.
- **zero-retention(선택)**: 이력 DB 미기록(메모리 전용). 리포트는 사용자가 지정한
  경로에만 저장됩니다.

---

## 테스트

```powershell
.\.venv\Scripts\activate
pytest -q
```

네트워크 없이 도메인 규칙, 익명화 왕복, 플레이북 정렬, 관할/벤치마크 로딩, 스키마
하드닝, 리포트 생성(DOCX, 한/영)을 검증합니다.

## 패키징

`build/README.md` 참고 (PyInstaller onedir → Inno Setup 설치 프로그램).

---

## ⚠️ 면책 / 검수 주의

- 본 도구의 모든 출력은 **일반 정보 제공이며 법률 자문이 아닙니다.**
- `data/jurisdiction/*.json` 의 관할별 법리 데이터는 **검수 대상 초안**입니다. AI 입법은
  빠르게 변동하므로, 실제 사용 전 해당 관할의 자격 있는 변호사 검수가 필요합니다.
- 모델 출력은 부정확할 수 있으므로 중요한 의사결정 전 전문가 확인을 권장합니다.
