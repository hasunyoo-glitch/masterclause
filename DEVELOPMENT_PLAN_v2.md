# AI Music Contract Analyzer (v2) — Windows 데스크탑 앱 개발 계획서

> 음악 아티스트 · 엔터테인먼트 변호사 · 음반사를 위한, 음악 계약서의 AI 관련 조항을 분석하는 **Windows 데스크탑 애플리케이션**
>
> 본 문서는 기존 `DEVELOPMENT_PLAN.md`(macOS · Electron 기준)를 확장·대체합니다. 변경된 요구사항을 반영해 플랫폼, 스택, 사용자 플로우, 도메인 모델을 갱신했습니다.

---

## 0. 기존 계획 대비 변경 요약

| 항목 | 기존 (v1) | 신규 (v2) |
|---|---|---|
| 플랫폼 | macOS DMG | **Windows 데스크탑 (.exe / installer)** |
| UI 스택 | Electron + React + TypeScript | **PySide6 (Qt) 네이티브 GUI** (1순위 추천) |
| 웹 의존 | Chromium 렌더러 사용 | **웹 미사용. 순수 네이티브 데스크탑 GUI** |
| 백엔드 통신 | FastAPI + HTTP(127.0.0.1) + IPC | **인프로세스 호출 (서버·IPC 불필요)** |
| 입출력 | 파일 업로드만 | **업로드 + 출력 저장 경로 지정** |
| 분석 전 옵션 | 없음 (설정에 일부) | **입장 / 출력 언어 / 관할(주 포함)을 분석 직전 확정** |
| 결과물 | 화면 표시 위주 | **지정 경로에 리포트 파일(DOCX/PDF) 저장** |

세 가지 신규 옵션은 다음과 같습니다.

1. **입장(Perspective)**: 엔터테인먼트 변호사 vs 아티스트 vs 음반사 측
2. **출력 언어(Output Language)**: 한글 vs 영문
3. **관할(Jurisdiction)**: 대한민국 vs 미국 (미국이면 주(state)까지 선택)

---

## 1. 제품 개요

| 항목 | 내용 |
|---|---|
| 제품명 | AI Music Contract Analyzer |
| 형태 | Windows 데스크탑 앱 (PySide6/Qt, 단일 .exe 또는 installer) |
| 대상 사용자 | 음악 아티스트, 엔터테인먼트 변호사, 음반사 임원 |
| 핵심 가치 | 계약서 PDF/DOCX를 올리고 옵션을 확정하면, AI 관련 위험 조항을 자동 탐지하고 위험도 · 산업 표준 비교 · 관할별 법리 · 협상 전략까지 담은 리포트를 생성해 지정 경로에 저장 |
| 차별점 | (1) 조항별 집행가능성(enforceability) 판단 (2) 사용자 입장에 맞춘 관점별 위험 평가 (3) 관할(KR/US-주)별 법리 분석 (4) 협상 플레이북(walk-away 포함) (5) 한글·영문 리포트 출력 |

### 핵심 원칙
1. **로컬 우선(Local-first)**: 모든 파일 처리는 로컬에서 수행, 클라우드 저장 없음. 외부 통신은 Anthropic API 호출뿐.
2. **프라이버시**: API 키는 OS 자격 증명 저장소에 보관, 전송 전 익명화 옵션, zero-retention 모드.
3. **법률 등급 분석**: 조항 원문(verbatim) 보존, 법적 근거(legal basis) 명시, "법률 자문 아님" 고지.
4. **관점 명시성**: 모든 위험 평가는 "누구 입장에서의 위험인가"를 전제로 한다. 입장이 바뀌면 같은 조항의 위험도가 바뀔 수 있음을 명확히 한다.

---

## 2. 기술 스택

### 2.1 권장 스택 (1순위)

**GUI / 앱 셸**
- **Python** 3.11+ (Windows용 공식 배포판. v1의 macOS 3.9.6 제약은 Windows에서는 해당 없음)
- **PySide6** (Qt 6) — 네이티브 위젯, 파일 다이얼로그, 멀티스레드(QThread)
- **qt-material** 또는 자체 QSS 스타일 (선택. 장식 최소화, 깔끔한 기본 테마)

**코어 / 분석**
- **Anthropic SDK** (`anthropic`) — 모델은 설정 가능 (기본값은 4.x 추론 강한 모델, 비용 우선 시 경량 모델로 전환). 정확한 모델 문자열·가격은 docs.claude.com에서 확인 후 `config`에 고정.
- **PyMuPDF** + **pdfplumber** (PDF 파싱), **python-docx** (DOCX 파싱 및 리포트 생성)
- **Pydantic** v2 — 도메인 모델 단일 진실 공급원(아래 4장). v1의 React/백엔드 모델 이중화 문제를 원천 제거.
- **SQLAlchemy** 2 + **SQLite** (`%APPDATA%/ai-contract-analyzer/contracts.db`) — 분석 이력 (선택 기능)

**저장 / 보안**
- **keyring** — Windows 자격 증명 관리자(Credential Manager)에 API 키 저장 (v1의 electron-store 대체)
- 설정 파일은 `%APPDATA%/ai-contract-analyzer/config.json` (키 제외)

**리포트 출력**
- **python-docx** (DOCX, 기본) — Times New Roman, 단색, 장식 없음, 법무 메모 스타일
- **docx2pdf** 또는 **LibreOffice headless** / **ReportLab** (PDF, 선택)

**패키징**
- **PyInstaller** (onedir 권장 → 안정적) 또는 **Nuitka**
- **Inno Setup** 또는 **NSIS** — Windows 설치 프로그램(.exe installer)
- (선택) 코드 서명 인증서로 SmartScreen 경고 완화

### 2.2 의사결정: PySide6 (확정)

스택은 **PySide6로 확정**한다. 요구사항(Windows · 웹 미사용 · 단순 GUI · 업로드/출력 경로/소수 옵션)에 가장 잘 맞고, 분석 엔진이 이미 전부 Python이라 단일 스택으로 통일된다. 참고로 두 후보의 비교는 다음과 같았다.

| 기준 | PySide6 (권장) | Electron 유지 |
|---|---|---|
| "웹 미사용" 요건 | 충족 (네이티브) | 내부 Chromium 사용 (웹 기술) |
| 스택 수 | 1 (Python) | 3 (TS/React + Electron + Python) |
| 백엔드 통신 | 인프로세스 함수 호출 | HTTP + IPC + child_process spawn |
| Claude Code 개발 난이도 | 낮음 | 높음 |
| Windows 패키징 | PyInstaller로 단순 | Python 동봉 + electron-builder 복잡 |
| 기존 v1 코드 재사용 | 코어(parser/analyzer/privacy) 재사용, UI는 신규 | UI 재사용 가능하나 모델 정렬 작업은 동일하게 필요 |
| UI 화려함 / 커스텀 | 보통 (충분) | 높음 (웹 CSS 자유도) |

v1의 React/Electron UI는 아직 스캐폴드 단계이고 모델 불일치로 전면 재작성이 예정돼 있었으므로, 지금 PySide6로 전환하는 한계비용은 낮다. (참고: 코어 모듈 parser/analyzer/privacy는 그대로 재사용한다.)

> 본 계획서의 이후 내용은 PySide6 기준으로 작성한다.

---

## 3. 아키텍처 (PySide6 단일 프로세스)

```
┌──────────────────────────────────────────────────────────────┐
│  Windows Desktop App (단일 Python 프로세스)                    │
│                                                              │
│  ┌────────────────────────┐   ┌──────────────────────────┐  │
│  │  UI Layer (PySide6)     │   │  Worker Thread (QThread)  │  │
│  │  • 메인/업로드 화면      │──▶│  분석 파이프라인 실행      │  │
│  │  • 옵션 화면             │   │  (UI 비차단)               │  │
│  │  • 진행 화면 (progress)  │◀──│  signal로 진행률/결과 전달 │  │
│  │  • 결과 화면             │   └──────────┬───────────────┘  │
│  └────────────────────────┘              │                   │
│                                          ▼                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Core (인프로세스 함수 호출, 서버 없음)                    ││
│  │  parser → preprocessor(익명화) → analyzer(Claude) →      ││
│  │  jurisdiction → benchmark → playbook → report_writer     ││
│  └─────────────────────────────────────────────────────────┘│
│                          │                │                   │
│                          ▼                ▼                   │
│        SQLite (이력, 선택)        지정 경로에 리포트 저장        │
│        keyring (API 키)                                       │
└──────────────────────────────────────────────────────────────┘
                    │ (외부 통신은 이것 하나)
                    ▼
              Anthropic API
```

### 권장 프로젝트 구조
```
ai-contract-analyzer/
├─ app/
│  ├─ main.py                  # 앱 진입점 (QApplication)
│  ├─ ui/
│  │  ├─ main_window.py        # 메인 윈도우 + 화면 전환(QStackedWidget)
│  │  ├─ screen_upload.py      # 파일 선택 + 출력 경로 지정
│  │  ├─ screen_options.py     # 입장/언어/관할(주) 옵션
│  │  ├─ screen_progress.py    # 진행률 표시 + 취소
│  │  ├─ screen_result.py      # 결과 요약 + 저장 완료 안내
│  │  ├─ screen_settings.py    # API 키 입력/검증/교체, 기본 옵션
│  │  └─ widgets/              # RiskScoreCard, ClauseList, FlagBadge 등
│  ├─ worker.py                # QThread 워커 (분석 파이프라인 호출)
│  └─ state.py                 # 앱 상태(선택 파일, 옵션 등)
├─ core/
│  ├─ models.py                # Pydantic 도메인 모델 (단일 진실 공급원)
│  ├─ parser.py                # PDF/DOCX → 정규화 텍스트(+조항 위치)
│  ├─ privacy.py               # 익명화 / zero-retention
│  ├─ analyzer.py              # Claude 호출, 프롬프트 구성, 스키마 강제
│  ├─ jurisdiction.py          # KR / US-주별 법리 매핑
│  ├─ benchmarks.py            # 계약 유형별 산업 표준 데이터/판정
│  ├─ playbook.py              # 협상 플레이북 정렬(MUST_FIX/walk-away)
│  └─ report_writer.py         # AnalysisResult → DOCX/PDF
├─ data/
│  ├─ benchmarks/              # 유형별 표준 조항 데이터(JSON)
│  └─ jurisdiction/            # 관할별 법리 노트 데이터(JSON, 검수 대상)
├─ config.py                   # 경로, 모델명, 기본값
├─ tests/
├─ requirements.txt
└─ build/                      # PyInstaller spec, Inno Setup script
```

---

## 4. 도메인 모델 (Pydantic, 단일 진실 공급원)

> `core/models.py`에 정의. UI · 코어 · DB · 리포트가 모두 이 모델을 공유한다. (v1의 모델 이중화/불일치 이슈는 구조적으로 제거됨)

### 4.1 분류 체계 (v1 유지 + 확장)

- **ContractType** (9종): `recording_agreement` · `sync_license` · `distribution_deal` · `publishing_agreement` · `producer_agreement` · `co_publishing` · `management_agreement` · `performance_agreement` · `unknown`
- **RiskLevel(flag)**: `RED` / `YELLOW` / `GREEN`
- **Priority**: `MUST_FIX` / `SHOULD_FIX` / `NICE_TO_FIX`
- **Enforceability**: `LIKELY_ENFORCEABLE` / `CONTESTED` / `LIKELY_UNENFORCEABLE`
- **AIIssueType** (9종): `training_data_usage` · `ai_ownership` · `voice_cloning` · `synthetic_covers` · `future_technology` · `perpetual_license` · `class_action_waiver` · `identity_disclosure` · `ai_clause_absence`

### 4.2 신규 옵션 모델 (이번 변경의 핵심)

```python
class Perspective(str, Enum):       # 사용자 입장
    LAWYER = "lawyer"               # 엔터테인먼트 변호사 (의뢰인 자문 관점)
    ARTIST = "artist"               # 아티스트 본인 보호 관점
    LABEL  = "label"                # 음반사/레이블 관점

class OutputLanguage(str, Enum):
    KO = "ko"
    EN = "en"

class Jurisdiction(str, Enum):      # GUI 노출은 KR/US, 내부는 확장 가능
    KR = "KR"
    US = "US"
    # (확장 여지: EU, UK, JP, UNKNOWN)

class USState(str, Enum):           # jurisdiction == US 일 때만 사용
    CA = "CA"               # California
    NY = "NY"               # New York
    TN = "TN"               # Tennessee
    DC = "DC"               # Washington D.C. (주는 아닌 연방 특별구이나 관할로 취급)
    OTHER = "OTHER"         # 그 외는 직접 입력

class AnalysisOptions(BaseModel):   # GUI에서 확정되어 분석에 전달
    input_file_path: str
    output_path: str                # 리포트 저장 경로(디렉터리 또는 파일)
    perspective: Perspective
    output_language: OutputLanguage
    jurisdiction: Jurisdiction
    us_state: USState | None = None # US일 때 필수
    output_format: Literal["docx", "pdf", "both"] = "docx"
    # 선택: 사용자가 이 계약에서 가장 우려하는 점 (자유 입력, 최대 300자)
    user_concern: str | None = Field(default=None, max_length=300)
    # 프라이버시
    anonymize_before_analysis: bool = False
    zero_retention: bool = False
```

> 검증 규칙: `jurisdiction == US` 이면 `us_state` 필수. KR이면 무시.

### 4.3 분석 결과 구조 (`AnalysisResult`)

| 필드 | 타입 | 설명 |
|---|---|---|
| `options` | `AnalysisOptions` | 어떤 입장/언어/관할로 분석했는지 결과에 동봉 (재현성) |
| `overview` | `ContractOverview` | 계약 유형, 당사자, 발효일, 기간, 영역, 준거법, 관할 |
| `risk_score` | `RiskScore` | 종합 0–100 + 세부(저작권/수익배분/통제권/법적구제). **입장 기준으로 계산됨** |
| `ai_clauses` | `AIClause[]` | 조항별 원문 · 요약 · flag · 집행가능성 · `impact_on_you` · 수정안 · 법적근거 |
| `benchmarks` | `BenchmarkItem[]` | 산업 표준 대비 (FAVORABLE/NEUTRAL/UNFAVORABLE, 입장 기준) |
| `jurisdiction_notes` | `JurisdictionNote[]` | 관할별 적용법 · 분석 · 준거법 충돌 여부 |
| `negotiation_playbook` | `NegotiationItem[]` | 협상 전략, walk-away 플래그, 제안 수정안 |
| `concern_advice` | `ConcernAdvice \| None` | **사용자가 우려(`user_concern`)를 입력한 경우에만** 생성. 분석 결과에 근거해 그 우려에 직접 답하는 맞춤 조언 |
| `recommendation` | `SIGN` / `NEGOTIATE` / `REJECT` | 최종 권고 (입장 반영) |
| `disclaimer` | `str` | 법률 자문 아님 고지 |

신규 필드 `AIClause.impact_on_you`: 선택한 입장에서 이 조항이 의미하는 바를 한 문장으로 설명 (예: 아티스트에게는 "당신의 목소리를 무기한 AI 학습에 사용할 권리를 음반사에 부여함").

신규 모델 `ConcernAdvice` (우려 입력 시에만 생성):

```python
class ConcernAdvice(BaseModel):
    concern_text: str                  # 사용자가 입력한 원문 우려 (그대로 보존)
    direct_answer: str                 # 우려에 대한 직접적 답변 (선택 언어/입장 반영)
    relevant_clause_ids: list[str]     # 이 우려와 직접 관련된 조항(ai_clauses)의 id 참조
    risk_assessment: RiskLevel         # 그 우려 관점에서의 위험도(RED/YELLOW/GREEN)
    recommended_actions: list[str]     # 우려 해소를 위한 구체적 행동(협상 포인트/문구 등)
```

> 원칙: `concern_advice`는 새 사실을 지어내지 않고 **이미 산출된 분석(ai_clauses/benchmarks/jurisdiction_notes)에 근거**해 우려에 답한다. 관련 조항이 없으면 "해당 우려와 직접 관련된 조항을 찾지 못함"을 명시하고, 일반론 또는 누락 위험(`ai_clause_absence`) 관점에서 보완 조언한다.

---

## 5. GUI 설계 및 사용자 플로우 (신규 핵심)

화면은 `QStackedWidget`으로 단계 전환. 모든 장시간 작업은 QThread 워커에서 실행하여 UI를 멈추지 않게 한다.

### 5.1 단계별 흐름

**0단계. API 키 입력 (GUI에서 처리)**
- Anthropic API 키는 **GUI에서 직접 입력**한다. 환경변수나 파일 수동 편집을 요구하지 않는다.
- 키 미설정 시: 앱 첫 실행에서 키 입력 화면/다이얼로그를 띄움.
  - `QLineEdit`(`EchoMode.Password`) + [보기/숨김] 토글 + [붙여넣기]
  - [연결 테스트] 버튼: 입력한 키로 가벼운 검증 호출을 보내 유효성 확인(성공/실패 표시)
  - [저장]: 검증 통과 시 `keyring`으로 Windows 자격 증명 관리자에 저장
- 키 설정됨: 이후 실행에서 자동 로드, 분석 화면으로 바로 진입.
- 설정 화면에서 **언제든 키 교체/삭제** 가능. 저장된 키는 화면에 평문 재노출하지 않고 `sk-...****` 형태 마스킹 + "설정됨" 상태만 표시.
- 분석 시도 시 키가 없거나 무효면 안내 후 키 입력 화면으로 유도.

**1단계. 파일 선택 + 출력 경로 지정** (`screen_upload.py`)
- 계약서 선택: `QFileDialog.getOpenFileName` (필터: `*.pdf *.docx`). 드래그앤드롭도 지원.
- 출력 저장 경로 지정: `QFileDialog.getExistingDirectory`(폴더) 또는 `getSaveFileName`(파일명까지)
- 입력 파일명 미리보기, 페이지/문단 수 표시(파싱 미리보기)
- [다음] 버튼

**2단계. 옵션 설정** (`screen_options.py`) — 확정 후에만 분석 시작
- (1) **입장**: 라디오 버튼 3택 (엔터테인먼트 변호사 / 아티스트 / 음반사)
  - 각 옵션에 한 줄 설명(예: "아티스트: 당신의 권리 보호 관점에서 위험을 평가합니다")
- (2) **출력 언어**: 토글 (한글 / 영문)
- (3) **관할**: 라디오 (대한민국 / 미국)
  - "미국" 선택 시 → 주(state) 드롭다운 활성화(CA / NY / TN / DC, 그 외는 OTHER 직접 입력)
  - "대한민국" 선택 시 → 주 드롭다운 비활성화
- (선택) 프라이버시: [전송 전 익명화] [zero-retention] 체크박스
- (선택) **가장 큰 우려**: 여러 줄 텍스트 입력(`QPlainTextEdit`), 안내 문구 "이 계약에서 가장 걱정되는 점을 적어주세요 (선택)". 실시간 글자 수 카운터(0/300), 300자 초과 입력 차단. 비워두면 일반 분석만 수행.
- 유효성: US인데 주 미선택이면 [분석 시작] 비활성 (우려 입력은 선택이라 유효성에 영향 없음)
- [분석 시작] 버튼 (옵션 확정 = 이 버튼 클릭)

**3단계. 분석 진행** (`screen_progress.py`)
- 단계 표시: 파싱 → (익명화) → AI 분석 → 관할 매핑 → 벤치마크 → 리포트 생성
- `QProgressBar` + 현재 단계 라벨, [취소] 버튼 (워커 중단)
- 비용 안내(선택): 예상 토큰/비용 표시

**4단계. 결과** (`screen_result.py`)
- 화면 요약: 종합 위험 점수, 권고(SIGN/NEGOTIATE/REJECT), RED 조항 수, walk-away 이슈
- 조항 리스트(접이식), 협상 플레이북 요약
- 우려를 입력했다면: **"당신의 우려에 대한 조언"** 블록을 눈에 띄게 상단 노출(직접 답변 + 관련 조항 링크 + 권고 행동)
- "리포트가 `{output_path}`에 저장되었습니다" 안내
- 버튼: [저장 폴더 열기] [리포트 열기] [새 분석] [이력 보기(선택)]

### 5.2 상태 모델
`app/state.py`가 선택 파일·출력 경로·옵션을 보관하고, [분석 시작] 시 `AnalysisOptions`로 직렬화하여 워커에 전달.

---

## 6. 분석 엔진 (입장·언어·관할 반영)

### 6.1 입장(Perspective) 반영 = 이번 설계의 지적 핵심

같은 조항이라도 **누구 입장이냐에 따라 위험도가 달라진다**. 예: "음반사가 아티스트 음원을 AI 학습에 무기한 사용" 조항은 아티스트에게 RED, 음반사에게는 GREEN/유리에 가깝다.

반영 지점:
- **시스템 프롬프트**: "당신은 {입장}을 대리/대변하여 분석한다"를 명시. 위험은 그 입장의 이익 기준으로 평가.
- **flag 산정**: 동일 조항도 입장에 따라 RED/YELLOW/GREEN이 달라질 수 있음.
- **`impact_on_you`**: 해당 입장에서의 영향 한 줄 설명.
- **negotiation_playbook 방향성**: 변호사/아티스트는 "이 조항을 어떻게 완화/삭제할까", 음반사는 "이 조항이 방어 가능한가, 표준 범위인가".
- **recommendation**: 입장의 이익 기준 종합 권고.

> 변호사(LAWYER) 입장은 "중립적 법률 분석 + 의뢰인 자문" 톤으로, 집행가능성·법적 근거를 더 정밀하게. 아티스트(ARTIST)는 평이한 언어 + 보호 중심. 음반사(LABEL)는 리스크 노출·방어가능성·표준 대비 중심.

### 6.2 출력 언어(Output Language)
- Claude 출력 텍스트(요약, 분석, 수정안, 노트)는 선택 언어(ko/en)로 생성.
- **조항 원문(verbatim)은 원본 언어 그대로 보존** (번역하지 않음). 필요 시 번역은 별도 표기.
- 리포트 라벨·제목도 선택 언어로 렌더링.
- 영문 출력 시: 법무 메모 톤, 법적 근거는 간결한 인용 형태(필요 시 Bluebook 스타일 약식). 한글 출력 시: 자연스러운 실무 한국어.

### 6.3 관할(Jurisdiction + US State)
- `core/jurisdiction.py`가 `(jurisdiction, us_state)` → 적용법/쟁점 세트를 매핑하고, 그 컨텍스트를 프롬프트에 주입.
- **대한민국(KR)**: 저작권법, 전속계약 관련 공정거래 쟁점(공정위 표준전속계약서), 약관규제법(약관의 공정성), 퍼블리시티/초상·음성 보호(부정경쟁방지법 개정 관련), 신탁관리(KOMCA 등). AI 음성 복제·합성 커버 관련 국내 논의 반영.
- **미국(US) + 주**: 준거법·관할(governing law/venue) + 주별 엔터테인먼트/퍼블리시티/디지털 복제 쟁점. 지원 관할(검증 필요):
  - California: 7년 룰(Labor Code §2855), 퍼블리시티권(Civ. Code §3344), AI 디지털 복제 관련 최근 입법(AB 2602 등 계약상 디지털 레플리카 규율)
  - New York: 퍼블리시티권(Civil Rights Law §50–51) 및 디지털 레플리카 관련 조항
  - Tennessee: ELVIS Act(음성/초상 AI 보호)
  - Washington D.C.: 연방 특별구로 주(state)는 아니나 별도 관할로 취급. 연방법 중심 + D.C. 지역 쟁점 매핑
  - 그 외(OTHER): 사용자 직접 입력 시 연방 공통 쟁점 위주로 분석하고 주별 특수성은 일반론으로 처리
- **준거법 ↔ 관할 충돌 탐지**: 계약서가 정한 준거법과 사용자가 선택한 관할이 다르면 `JurisdictionNote.conflict = true`로 경고.

> 주의: 관할별 법리 데이터는 정확도가 핵심이며 **전문가 검수가 필요**하다(9장 리스크). `data/jurisdiction/*.json`을 검수 대상 데이터셋으로 분리 관리한다.

### 6.4 분석 파이프라인
1. **parser**: PDF/DOCX → 정규화 텍스트 + 조항 경계 추정(원문 정확 추출용)
2. **privacy**(옵션): 익명화 마스킹 후 전송
3. **계약 유형 자동 감지** → 유형별 프롬프트 분기
4. **AIIssueType 탐지** + 조항 원문 verbatim 추출
5. **집행가능성 + 법적 근거** 판단 (입장·관할 컨텍스트 주입)
6. **벤치마크/플레이북** 생성
7. **report_writer** → 지정 경로 저장
- **출력 스키마 강제**: Claude에 JSON 스키마(=`AnalysisResult`)를 주고 그 형식만 반환하게 함. Pydantic으로 검증·재시도.
- **prompt caching**: 시스템 프롬프트/스키마/관할 컨텍스트를 캐시해 비용·지연 절감.
- **긴 계약서**: 청크 분할 또는 컨텍스트 한도 관리, 중복 해시 캐시.
- 우려 입력 시 본 분석 직후 6.5의 맞춤 조언 단계를 이어서 수행.

### 6.5 사용자 우려 맞춤 조언 (`user_concern` 입력 시)

`user_concern`이 비어 있지 않을 때만 추가 단계를 수행한다.

- **실행 시점**: 본 분석(ai_clauses/benchmarks/jurisdiction_notes/playbook)이 끝난 뒤, 그 결과를 컨텍스트로 별도 호출하여 `ConcernAdvice`를 생성한다. (분석 일관성 확보 + 새 사실 날조 방지)
- **입력**: 사용자 우려 원문 + 완성된 `AnalysisResult`(우려 필드 제외) + 입장 + 출력 언어 + 관할.
- **출력**: 우려에 대한 직접 답변, 관련 조항 id 매핑, 우려 관점의 위험도, 구체적 행동 권고.
- **언어·입장 반영**: 답변은 선택 언어로, 선택 입장의 이익 관점에서 작성.
- **근거 제약**: ai_clauses 등 이미 산출된 근거만 사용. 관련 조항이 없으면 그 사실을 명시하고 일반론/누락위험으로 안내.
- **프롬프트 캐시**: 앞 분석에서 만든 시스템/스키마 캐시 재사용으로 비용 절감.

---

## 7. 출력 리포트 생성 (신규)

`core/report_writer.py` — `AnalysisResult` → 파일.

- **형식**: DOCX 기본(python-docx), PDF 선택. `output_format` 옵션으로 선택.
- **스타일**: Times New Roman, 단색(장식 색상 없음), 깔끔한 법무 메모 구조, AI 티 나는 과한 서식 지양.
- **언어**: `output_language`에 따라 한글/영문 렌더링.
- **구성**:
  1. 표지/머리말: 계약 유형, 당사자, 분석 입장·언어·관할, 생성일
  2. 종합 위험 점수 + 최종 권고
  3. 핵심 발견(RED/walk-away 우선)
  4. 조항별 상세: 원문(verbatim) · 요약 · flag · 집행가능성 · 영향(impact_on_you) · 제안 수정안 · 법적 근거
  5. **당신의 우려에 대한 조언** (우려 입력 시에만): 우려 원문, 직접 답변, 관련 조항, 우려 관점 위험도, 권고 행동
  6. 산업 표준 벤치마크
  7. 관할별 법리 노트(준거법 충돌 경고 포함)
  8. 협상 플레이북(우선순위·walk-away·수정안)
  9. 면책 고지("법률 자문 아님")
- 저장 후 결과 화면에서 경로 안내 + 폴더/파일 열기 제공.

---

## 8. 개발 환경 (Windows 기준)

1. **Python**: Windows용 공식 3.11+ 설치, 프로젝트 가상환경 `python -m venv .venv` 사용. (v1의 macOS 시스템 파이썬 3.9.6 제약은 Windows에 해당 없음)
2. **의존성**: `pip install -r requirements.txt`. PyMuPDF/pdfplumber/python-docx/PySide6/anthropic/pydantic/SQLAlchemy/keyring.
3. **실행**: `python -m app.main`
4. **GUI 디버깅**: PySide6 위젯은 핫리로드가 약하므로, 코어 로직은 `tests/`로 단위 테스트하고 UI는 별도 검증.
5. **경로**: 사용자 데이터는 `%APPDATA%/ai-contract-analyzer/`. 하드코딩 금지, `config.py`에서 관리.
6. **인코딩**: Windows 콘솔 한글 깨짐 방지 위해 UTF-8 강제(`PYTHONUTF8=1`).

---

## 9. 단계별 실행 계획

### Phase 0 — 스캐폴드 및 코어 이식
- [ ] 프로젝트 구조 생성, `requirements.txt`, `config.py`
- [ ] `core/models.py`에 Pydantic 도메인 모델 확정 (4장 전체, `AnalysisOptions` 포함)
- [ ] v1의 `parser.py` · `privacy.py` 이식 및 Windows 경로 대응
- [ ] keyring 기반 API 키 저장/로드

### Phase 1 — GUI 골격 + 사용자 플로우 (신규 핵심)
- [ ] 메인 윈도우 + QStackedWidget 4화면 전환
- [ ] 1단계: 파일 선택 + 출력 경로 지정 (다이얼로그, 드래그앤드롭)
- [ ] 2단계: 입장/언어/관할(주) 옵션 화면 + 유효성(US→주 필수)
- [ ] 2단계: 선택적 우려 입력(QPlainTextEdit, 300자 카운터/제한)
- [ ] 3단계: QThread 워커 + 진행률/취소
- [ ] 4단계: 결과 요약 + 저장 안내 + 폴더 열기
- [ ] 설정 화면(`screen_settings.py`): API 키 GUI 입력 + 보기/숨김 + [연결 테스트] 검증 + keyring 저장 + 교체/삭제 + 마스킹 표시
- [ ] 키 미설정 시 첫 실행에서 키 입력 화면으로 유도, 분석 전 키 유효성 확인

### Phase 2 — Claude 분석 엔진
- [ ] `analyzer.py`: 출력 JSON 스키마를 `AnalysisResult`와 1:1 정합, Pydantic 검증/재시도
- [ ] 계약 유형 자동 감지 → 유형별 프롬프트 분기
- [ ] 9종 AIIssueType 탐지 + 조항 원문 verbatim 추출
- [ ] 집행가능성 + 법적 근거 인용
- [ ] **입장(Perspective) 반영 로직** (위험도/영향/플레이북/권고)
- [ ] **출력 언어 반영** (생성 텍스트 ko/en, 원문 보존)
- [ ] prompt caching, 긴 계약서 청크/캐시

### Phase 3 — 관할 법리 분석
- [ ] `jurisdiction.py`: KR / US-주 → 적용법·쟁점 매핑
- [ ] AI 음성복제·디지털 레플리카 관련 관할별 쟁점 반영 (검수 데이터셋)
- [ ] 준거법 ↔ 관할 충돌 탐지(`JurisdictionNote.conflict`)
- [ ] `data/jurisdiction/*.json` 분리 및 검수 절차 명시

### Phase 4 — 산업 표준 벤치마킹
- [ ] 유형별 표준 조항 데이터(`data/benchmarks/*.json`: royalty rate, term length 등)
- [ ] `BenchmarkItem` 생성 + 입장 기준 FAVORABLE/NEUTRAL/UNFAVORABLE 판정 + UI 표시

### Phase 5 — 협상 플레이북 + 우려 맞춤 조언
- [ ] `playbook.py`: 우선순위 정렬(MUST_FIX 우선), walk-away 강조
- [ ] 수정안(proposed revision) 결과 화면 복사/내보내기
- [ ] `user_concern` 입력 시 `ConcernAdvice` 생성(본 분석 결과 근거, 입장·언어 반영, 근거 없는 날조 방지)
- [ ] 결과 화면·리포트에 우려 조언 블록 노출

### Phase 6 — 리포트 출력
- [ ] `report_writer.py`: DOCX 생성(Times New Roman, 단색, 메모 구조)
- [ ] 한글/영문 렌더링, 면책 고지
- [ ] PDF 출력(선택) 및 지정 경로 저장 검증

### Phase 7 — 이력 / 비교 (선택)
- [ ] SQLite 이력 저장/조회, 이력 화면
- [ ] (선택) 최대 3개 비교 모드 + 종합 권고

### Phase 8 — 프라이버시 & 보안
- [ ] `anonymize_before_analysis` 강화(이름·식별정보 마스킹)
- [ ] `zero_retention` (디스크 미기록, 메모리 전용)
- [ ] (선택) `auto_delete_after_days`
- [ ] keyring 키 보관 검증, 설정에 키 미노출 확인

### Phase 9 — 패키징 & 배포 (Windows)
- [ ] PyInstaller(onedir) 빌드, Anthropic SDK/PyMuPDF 등 동봉 검증
- [ ] Inno Setup/NSIS 설치 프로그램 작성
- [ ] (선택) 코드 서명으로 SmartScreen 경고 완화
- [ ] 클린 Windows 머신 설치/실행 테스트

---

## 10. 데이터 영속화 · 설정 · 보안

| 항목 | 위치/방식 |
|---|---|
| API 키 | GUI에서 입력·검증·교체. Windows 자격 증명 관리자(keyring)에 저장. 화면 재노출 금지(마스킹) |
| 설정 | `%APPDATA%/ai-contract-analyzer/config.json` (기본 입장·언어·관할 등, 키 제외) |
| 이력 DB | `%APPDATA%/ai-contract-analyzer/contracts.db` (SQLite, 선택 기능) |
| 리포트 | 사용자 지정 출력 경로 |
| zero-retention | 메모리 전용, DB/디스크 미기록 |

---

## 11. 리스크 & 미해결 결정사항

| 항목 | 리스크 | 대응 |
|---|---|---|
| 스택 전환 | v1 React/Electron UI 폐기 | UI는 신규, 코어(parser/analyzer/privacy)는 재사용. 모델 정렬 작업은 어차피 필요했음 |
| 입장별 위험 평가 일관성 | 같은 조항이 입장 따라 달라져 혼란 가능 | 결과에 입장 명시, `impact_on_you`로 근거 제시 |
| KR/US-주 법리 정확도 | 법 데이터 신뢰성, AI 입법은 빠르게 변동 | 검수 데이터셋 분리, "법률 자문 아님" 고지, 출처/시점 명기 |
| 모델명·가격 변동 | 하드코딩 시 오류/비용 | `config.py`로 모델명 분리, docs.claude.com에서 확인 후 고정 |
| PyInstaller 번들 | PyMuPDF 등 네이티브 의존 누락 가능 | onedir 빌드 + 클린 머신 테스트, hidden imports 점검 |
| Claude 비용 | 긴 계약서 다회 분석 | prompt caching + 중복 해시 캐시 + 비용 안내 |
| Qt UI 차단 | 분석 중 멈춤 | QThread 워커 필수, signal 기반 진행률 |
| 법률 면책 | 자문 오인 | UI·리포트 양쪽에 disclaimer 고정 |

---

## 12. 다음 액션

> **즉시 시작: Phase 0 → Phase 1.**
> (1) `core/models.py`에 `AnalysisOptions`(입장/언어/관할-주/출력경로) 포함 전체 도메인 모델을 Pydantic으로 확정한다.
> (2) v1의 parser/privacy 코어를 이식한다.
> (3) PySide6로 4단계 플로우(업로드+출력경로 → 옵션확정 → 진행 → 결과저장) 골격을 세운다.
>
> 이 순서로 가면 "업로드 → 옵션 확정 → 분석 → 지정 경로 저장"이라는 핵심 사용자 경험이 가장 먼저 동작하게 된다.
