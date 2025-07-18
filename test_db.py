# test_db.py - 빠른 테스트를 위한 소수 종목 데이터베이스 구축

from models import Session, init_db
from data_importer import *
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sample_korean_stocks():
    """테스트용 소수 종목 목록"""
    return [
        {'symbol': '005930.KS', 'krx_code': '005930', 'name': '삼성전자', 'market': 'KOSPI'},
        {'symbol': '000660.KS', 'krx_code': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI'},
        {'symbol': '035420.KS', 'krx_code': '035420', 'name': 'NAVER', 'market': 'KOSPI'},
        {'symbol': '035720.KS', 'krx_code': '035720', 'name': '카카오', 'market': 'KOSPI'},
        {'symbol': '005490.KS', 'krx_code': '005490', 'name': 'POSCO홀딩스', 'market': 'KOSPI'},
        {'symbol': '293490.KQ', 'krx_code': '293490', 'name': '카카오게임즈', 'market': 'KOSDAQ'},
        {'symbol': '259960.KQ', 'krx_code': '259960', 'name': '크래프톤', 'market': 'KOSDAQ'},
        {'symbol': '068270.KQ', 'krx_code': '068270', 'name': '셀트리온', 'market': 'KOSDAQ'}
    ]

def test_build_database():
    """테스트용 데이터베이스 구축"""
    db = Session()
    try:
        print("테스트 데이터베이스 초기화를 시작합니다...")
        
        # 테이블 생성
        init_db()
        
        # 샘플 종목 정보 저장
        sample_symbols = get_sample_korean_stocks()
        print(f"샘플 종목 {len(sample_symbols)}개 저장 중...")
        
        for symbol_info in sample_symbols:
            symbol = symbol_info['symbol']
            existing_stock = db.query(Stock).filter_by(symbol=symbol).first()
            
            if not existing_stock:
                new_stock = Stock(
                    symbol=symbol,
                    krx_code=symbol_info['krx_code'],
                    name=symbol_info['name'],
                    market=symbol_info['market'],
                    is_active=True
                )
                db.add(new_stock)
        
        db.commit()
        print("샘플 종목 저장 완료")
        
        # 6개월 데이터만 가져오기
        today = datetime.now().date()
        start_date = (today - timedelta(days=180)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        print(f"주가 데이터 수집 시작 (기간: {start_date} ~ {end_date})")
        
        # 각 종목별로 데이터 수집
        stocks = db.query(Stock).all()
        for stock in stocks:
            print(f"처리 중: {stock.name} ({stock.symbol})")
            
            # 주가 데이터 수집
            price_data = fetch_stock_price(stock.stock_id, stock.symbol, start_date, end_date)
            if price_data:
                save_price_data(stock.stock_id, price_data)
                print(f"  주가 데이터 {len(price_data)}개 저장 완료")
                
                # 기술적 지표 계산
                calculate_and_save_technical_indicators(stock.stock_id)
                print(f"  기술적 지표 계산 완료")
            else:
                print(f"  데이터 없음")
        
        # 시장 지수 데이터 수집
        print("시장 지수 데이터 수집 중...")
        fetch_and_save_market_indices(db, start_date, end_date)
        
        # 시장 통계 계산
        print("시장 통계 계산 중...")
        calculate_market_stats(db)
        
        print("테스트 데이터베이스 구축 완료!")
        
        # 결과 확인
        print("\n=== 구축 결과 ===")
        stock_count = db.query(Stock).count()
        price_count = db.query(DailyPrice).count()
        indicator_count = db.query(TechnicalIndicator).count()
        index_count = db.query(MarketIndex).count()
        stat_count = db.query(MarketStat).count()
        
        print(f"종목 수: {stock_count}")
        print(f"가격 데이터: {price_count}")
        print(f"기술적 지표: {indicator_count}")
        print(f"시장 지수: {index_count}")
        print(f"시장 통계: {stat_count}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"테스트 데이터베이스 구축 오류: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_build_database()