# run_update.py - 데이터베이스 업데이트 실행 스크립트

from .models import Session, init_db
from .data_importer import (
    build_initial_database, 
    update_daily_data, 
    update_full_technical_indicators,
    update_market_stats
)
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_task(task: str, **kwargs):
    """DB 업데이트 작업을 실행합니다."""
    db = Session()
    try:
        if task == "init":
            print("데이터베이스 초기화를 시작합니다...")
            init_db()  # 테이블 생성
            build_initial_database(db, years=kwargs.get('years', 3))
            print("초기화 완료.")
        elif task == "update":
            print("일일 데이터 업데이트를 시작합니다...")
            update_daily_data(db, days=kwargs.get('days', 2))
            print("업데이트 완료. 기술적 지표를 전체 재계산합니다...")
            update_full_technical_indicators(db)
            print("시장 통계를 재계산합니다...")
            update_market_stats(db)
            print("모든 작업 완료.")
        else:
            print("잘못된 작업입니다. 'init' 또는 'update'를 사용하세요.")
    except Exception as e:
        logger.error(f"작업 실행 중 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task_name = sys.argv[1]
        if task_name == "init":
            years = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            run_task("init", years=years)
        elif task_name == "update":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            run_task("update", days=days)
        else:
            print("사용법:")
            print("  python run_update.py init [years]    # 데이터베이스 초기화 (기본: 3년)")
            print("  python run_update.py update [days]   # 데이터 업데이트 (기본: 2일)")
    else:
        print("사용법:")
        print("  python run_update.py init [years]    # 데이터베이스 초기화 (기본: 3년)")
        print("  python run_update.py update [days]   # 데이터 업데이트 (기본: 2일)")