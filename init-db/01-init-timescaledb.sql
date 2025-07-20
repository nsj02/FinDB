-- TimescaleDB 초기화 스크립트
-- 이 스크립트는 TimescaleDB 확장을 활성화하고 기본 설정을 수행합니다.

\echo '=================================================='
\echo 'FinDB TimescaleDB 초기화 시작'
\echo '=================================================='

-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 데이터베이스 정보 출력
\echo 'PostgreSQL 버전:'
SELECT version();

\echo 'TimescaleDB 확장 정보:'
SELECT default_version, comment FROM pg_available_extensions WHERE name = 'timescaledb';

-- 데이터베이스 확인
\echo '현재 데이터베이스:'
SELECT current_database();

-- 기본 권한 설정
GRANT ALL PRIVILEGES ON DATABASE finance_db TO postgres;

\echo '=================================================='
\echo 'FinDB TimescaleDB 초기화 완료'
\echo '테이블 생성은 애플리케이션에서 수행됩니다.'
\echo '=================================================='