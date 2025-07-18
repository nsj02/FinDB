FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY *.py ./

# Cron 작업 설정 (매일 오후 3시 30분에 업데이트)
RUN echo "30 15 * * 1-5 cd /app && python run_update.py update 2" > /etc/cron.d/finance-update
RUN chmod 0644 /etc/cron.d/finance-update
RUN crontab /etc/cron.d/finance-update

# 환경변수 설정
ENV PYTHONPATH=/app
ENV DATABASE_URL=postgresql://postgres:password@localhost:5432/finance_db

# 초기화 스크립트 생성
RUN echo '#!/bin/bash\n\
# 데이터베이스 초기화\n\
python -c "from models import init_db; init_db()"\n\
\n\
# Cron 서비스 시작\n\
service cron start\n\
\n\
# 무한 대기 (컨테이너 유지)\n\
tail -f /dev/null' > /app/start.sh

RUN chmod +x /app/start.sh

# 헬스체크
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3 \
    CMD python -c "from models import Session; session = Session(); session.execute('SELECT 1'); session.close()" || exit 1

# 시작 스크립트 실행
CMD ["/app/start.sh"]