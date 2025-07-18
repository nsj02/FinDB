# 네이버클라우드 서버 배포 가이드

## 📋 사전 준비사항

### 1. 서버 스펙 권장사항
- **CPU**: 2코어 이상
- **메모리**: 4GB 이상
- **디스크**: 20GB 이상
- **OS**: Ubuntu 20.04 이상

### 2. 필수 소프트웨어 설치
```bash
# Docker 설치
sudo apt update
sudo apt install -y docker.io docker-compose

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
```

## 🚀 배포 단계

### 1. 코드 다운로드
```bash
git clone https://github.com/nsj02/FinDB.git
cd FinDB
```

### 2. 환경 설정
```bash
# 환경 변수 설정
cp .env.example .env
nano .env  # 비밀번호 변경
```

### 3. 방화벽 설정 (Optional)
```bash
# PostgreSQL 포트 (필요시)
sudo ufw allow 5432

# 또는 내부 접근만 허용
sudo ufw allow from 10.0.0.0/8 to any port 5432
```

### 4. 서비스 시작
```bash
# 컨테이너 시작
docker-compose up -d

# 상태 확인
docker-compose ps
```

### 5. 테스트 실행
```bash
# 소량 데이터로 테스트
docker-compose exec database-server python run_update.py test

# 전체 데이터 수집 (1년치)
docker-compose exec database-server python run_update.py init
```

## 🔍 모니터링

### 로그 확인
```bash
# 전체 로그
docker-compose logs -f

# 특정 컨테이너 로그
docker-compose logs -f database-server
```

### 데이터베이스 접속 확인
```bash
docker-compose exec timescaledb psql -U postgres -d finance_db
```

## ⚠️ 주의사항

1. **Yahoo Finance API 제한**
   - 너무 많은 요청 시 IP 차단 가능
   - VPN 사용 권장

2. **메모리 사용량**
   - 전체 데이터 수집 시 메모리 사용량 증가
   - 서버 모니터링 필요

3. **디스크 공간**
   - 1년치 데이터 약 5-10GB 예상
   - 여유 공간 확보 필요

## 🔄 자동화 설정

### Cron 작업 (일일 업데이트)
```bash
# 매일 오후 3시 30분에 업데이트
echo "30 15 * * * cd /path/to/FinDB && docker-compose exec database-server python run_update.py update" | crontab -
```

### 시스템 재시작 시 자동 실행
```bash
# docker-compose.yml에 restart: unless-stopped 이미 설정됨
# 시스템 재시작 후 자동으로 컨테이너 실행
```