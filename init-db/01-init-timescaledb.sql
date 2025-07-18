-- TimescaleDB 초기화 스크립트
-- 이 스크립트는 TimescaleDB 확장을 활성화하고 하이퍼테이블을 생성합니다.

-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 데이터베이스 정보 출력
SELECT version();
SELECT default_version, comment FROM pg_available_extensions WHERE name = 'timescaledb';

-- 하이퍼테이블 생성을 위한 함수들을 정의
-- 이 함수들은 애플리케이션에서 호출됩니다.