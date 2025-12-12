# AMS Bypass Web Query Application

PostgreSQL 데이터베이스의 `tenant.ams_bypass` 테이블을 조회하기 위한 웹 기반 쿼리 애플리케이션입니다.

## 기능

- **검색 기능**
  - Ship ID 필수 입력
  - Interface ID 선택적 LIKE 검색
  - 날짜 범위 필터링 (From Date, To Date)

- **데이터 표시**
  - JSON 데이터 파싱 및 테이블 형태 표시
  - 타임스탬프 변환 ($ship_posixmicros)
  - 접기/펼치기 가능한 결과 카드

- **보안**
  - SQL Injection 방지 (파라미터화된 쿼리)
  - 입력 유효성 검사
  - XSS 방지 (Jinja2 자동 이스케이프)

## 요구사항

- Python 3.8 이상
- PostgreSQL 데이터베이스 접근 권한

## 설치

1. 저장소 클론 또는 다운로드

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 데이터베이스 설정 (선택사항)
`config.py` 파일에서 데이터베이스 연결 정보를 확인하고 필요시 수정하세요:
```python
DB_HOST = 'pg-376fd4.vpc-cdb-kr.ntruss.com'
DB_PORT = 5432
DB_NAME = 'tenant_builder'
DB_USER = 'bypass'
DB_PASSWORD = 'qkdlvotm12!@'
```

## 실행

### 스크립트 사용 (권장)

**시작:**
```bash
./start.sh
```

**종료:**
```bash
./stop.sh
```

**재시작:**
```bash
./restart.sh
```

스크립트는 다음을 자동으로 처리합니다:
- 가상환경 확인 및 생성
- 의존성 설치
- 포트 충돌 확인 및 해결
- 백그라운드 실행
- PID 파일 관리
- 로그 파일 생성 (`app.log`)

### 수동 실행

개발 모드:
```bash
source venv/bin/activate
python app.py
```

애플리케이션은 `http://localhost:8765`에서 실행됩니다.

## 프로젝트 구조

```
amsbypass_web/
├── app.py                 # 메인 Flask 애플리케이션
├── config.py              # 설정 모듈 (DB 연결 정보 포함)
├── requirements.txt       # Python 패키지 의존성
├── .gitignore            # Git 무시 파일
├── README.md             # 프로젝트 문서
├── utils/                # 유틸리티 모듈
│   ├── __init__.py
│   ├── db.py            # 데이터베이스 연결 및 쿼리
│   └── parser.py        # JSON 파싱 및 타임스탬프 변환
├── templates/            # Jinja2 템플릿
│   └── search.html      # 검색 폼 및 결과 페이지
└── static/              # 정적 파일
    └── css/
        └── style.css    # 스타일시트
```

## 사용 방법

1. 웹 브라우저에서 `http://localhost:8765` 접속

2. 검색 조건 입력:
   - **Ship ID**: 필수 입력 (예: SHIP001)
   - **Interface ID**: 선택 입력 (부분 일치 검색, 예: ECS)
   - **From Date**: 선택 입력 (시작일, YYYY-MM-DD)
   - **To Date**: 선택 입력 (종료일, YYYY-MM-DD)

3. **Search** 버튼 클릭

4. 결과 확인:
   - 검색 결과는 카드 형태로 표시됩니다
   - 각 카드의 헤더를 클릭하여 JSON 데이터 테이블을 접기/펼치기 할 수 있습니다

## 데이터베이스 스키마

테이블: `tenant.ams_bypass`

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | bigserial | PRIMARY KEY |
| ship_id | text | 선박 ID (NOT NULL) |
| interface_id | text | 인터페이스 ID (NULLABLE) |
| json_data | text | JSON 데이터 (NULLABLE) |
| created_time | timestamp | 생성 시간 (NOT NULL) |
| server_created_time | timestamp | 서버 생성 시간 (NULLABLE) |

## JSON 데이터 처리

- 일반 키-값 쌍은 `desc`, `unit`, `value` 속성을 가진 객체로 파싱됩니다
- `$ship_posixmicros`는 마이크로초 단위 Unix timestamp를 읽기 쉬운 날짜/시간 형식으로 변환됩니다
- `$ship_sensornodeid`는 표시되지 않습니다 (무시)

## 문제 해결

### 데이터베이스 연결 오류
- `config.py` 파일의 데이터베이스 연결 정보를 확인하세요
- 네트워크 연결 및 방화벽 설정을 확인하세요

### 패키지 설치 오류
- Python 버전이 3.8 이상인지 확인하세요
- 가상환경이 활성화되어 있는지 확인하세요

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.

## 버전

현재 버전: 1.0.0

