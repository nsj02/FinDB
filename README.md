# FinDB - Financial Data Database

TimescaleDB 기반 주식 데이터 수집 및 저장 시스템입니다. 한국 주식 시장(KOSPI/KOSDAQ) 데이터를 효율적으로 수집하고 기술적 지표를 계산합니다.

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 환경변수 파일 생성
cp .env.example .env

# 필요시 환경변수 수정
vi .env
```

### 2. Docker로 실행
```bash
# 전체 시스템 실행 (데이터베이스 서버 + TimescaleDB)
docker-compose up -d

# 데이터베이스 초기화 및 데이터 수집
docker-compose exec database-server python run_update.py init 3
```

### 3. 로컬 개발 환경
```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python run_update.py init 3

# 데이터 업데이트
python run_update.py update
```

## 📊 주요 기능

### 데이터 수집
- **KOSPI/KOSDAQ 전종목** 실시간 데이터 수집
- **일일 주가 데이터** 저장 (시가, 고가, 저가, 종가, 거래량)
- **기업 기본 정보** 저장 (종목명, 섹터, 업종)

### 기술적 지표 계산
- **이동평균선** (MA5, MA10, MA20, MA60, MA120)
- **볼린저 밴드** (상단, 중단, 하단, 밴드폭)
- **RSI** (상대강도지수)
- **MACD** (Moving Average Convergence Divergence)
- **거래량 지표** (거래량 이동평균, 거래량 비율)
- **캔들 패턴** (도지, 해머 등)

### 시장 통계
- **시장 지수** (KOSPI, KOSDAQ 지수)
- **시장 통계** (상승/하락/보합 종목수, 총 거래량/거래대금)

## 🏗️ 기술 스택

- **Database**: TimescaleDB (PostgreSQL 기반)
- **ORM**: SQLAlchemy
- **Data Source**: yfinance, pykrx
- **Technical Analysis**: TA-Lib
- **Container**: Docker
- **Language**: Python 3.11

## 🔧 환경변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `DATABASE_URL` | `postgresql://postgres:password@localhost:5432/finance_db` | PostgreSQL 연결 문자열 |
| `MAX_WORKERS` | `4` | 데이터 수집 병렬 처리 수 |
| `UPDATE_INTERVAL_DAYS` | `1` | 데이터 업데이트 간격 (일) |

## 📁 데이터베이스 스키마

### 주요 테이블
- **stocks** - 주식 기본 정보
- **daily_prices** - 일일 주가 데이터
- **technical_indicators** - 기술적 지표
- **market_indices** - 시장 지수
- **market_stats** - 시장 통계

### 데이터 관계
```
stocks (1) -> (N) daily_prices
stocks (1) -> (N) technical_indicators
```

## 🔄 데이터 업데이트

### 수동 업데이트
```bash
# 초기 데이터 수집 (최근 3일)
python run_update.py init 3

# 일일 업데이트
python run_update.py update

# 특정 기간 업데이트
python run_update.py update --days 7
```

### 자동 업데이트
Cron 작업으로 매일 자동 업데이트 설정:
```bash
# 매일 오후 6시 업데이트
0 18 * * * cd /path/to/database-server && python run_update.py update
```

## 🐳 Docker 사용법

### 독립 실행
```bash
# 데이터베이스 서버만 실행
docker build -t yahoo-finance-database-server .
docker run -d \
  -e DATABASE_URL=postgresql://user:pass@db-host:5432/finance_db \
  yahoo-finance-database-server
```

### 전체 시스템 실행
```bash
# 데이터베이스 서버 + PostgreSQL 함께 실행
docker-compose up -d
```

## 📈 모니터링

### 데이터베이스 상태 확인
```bash
python test_db.py
```

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f database-server

# 로컬 실행시 로그 파일
tail -f logs/data_collection.log
```

### 데이터 확인
```sql
-- 수집된 종목 수 확인
SELECT COUNT(*) FROM stocks WHERE is_active = true;

-- 최근 데이터 확인
SELECT * FROM daily_prices ORDER BY date DESC LIMIT 10;

-- 기술적 지표 확인
SELECT * FROM technical_indicators ORDER BY date DESC LIMIT 10;
```

## 🔒 보안

- PostgreSQL 연결시 SSL 사용 권장
- 프로덕션 환경에서는 강력한 데이터베이스 비밀번호 사용
- 데이터베이스 접근 권한 최소화
- 정기적인 데이터베이스 백업 수행

## 🚀 배포

### 프로덕션 배포
```bash
# 프로덕션 환경변수 설정
export DATABASE_URL=postgresql://prod-user:prod-pass@prod-db:5432/finance_db

# 배포
docker-compose up -d

# 초기 데이터 수집
docker-compose exec database-server python run_update.py init 30
```

### 스케일링
- 데이터 수집 병렬 처리 수 증가: `MAX_WORKERS` 환경변수 조정
- 데이터베이스 연결 풀 크기 증가
- 필요시 읽기 전용 복제본 추가

## 📝 개발 가이드

### 새로운 데이터 소스 추가
1. `data_importer.py`에 새로운 수집 함수 추가
2. `models.py`에 필요한 테이블 정의
3. `run_update.py`에 업데이트 로직 추가

### 새로운 기술적 지표 추가
1. `models.py`의 `TechnicalIndicator` 테이블에 컬럼 추가
2. `data_importer.py`에 계산 로직 구현
3. 데이터베이스 마이그레이션 수행

### 데이터베이스 스키마 변경
```bash
# 스키마 변경 후 테이블 재생성
python -c "from models import init_db; init_db()"
```

## 🤝 연관 프로젝트

- [yahoo-finance-api-server](../yahoo-finance-api-server-repo) - API 서버

## 📊 성능 최적화

### 데이터베이스 인덱스
- `stocks.symbol` - 종목 코드 검색
- `daily_prices.date` - 날짜별 검색
- `daily_prices.stock_id, date` - 복합 인덱스
- `technical_indicators.date` - 기술적 지표 검색

### 배치 처리
- 대량 데이터 삽입시 배치 처리 사용
- 트랜잭션 단위 최적화
- 병렬 처리를 통한 수집 속도 향상

## 📄 라이센스

MIT License