# test_db.py - 빠른 테스트를 위한 소수 종목 데이터베이스 구축

from models import Session, init_db
from data_importer import *
import logging
import random

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_sample_price_data(stock_id, symbol, start_date, end_date, base_prices):
    """샘플 주가 데이터 생성"""
    from datetime import datetime, timedelta
    
    base_price = base_prices.get(symbol, 50000)
    current_price = base_price
    
    result = []
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    current_date = start
    while current_date <= end:
        # 주말 제외
        if current_date.weekday() < 5:
            # 변동률 (-3% ~ +3%)
            change_rate = random.uniform(-0.03, 0.03)
            
            # 가격 계산
            open_price = current_price
            high_price = open_price * (1 + abs(change_rate) * random.uniform(0.5, 1.5))
            low_price = open_price * (1 - abs(change_rate) * random.uniform(0.5, 1.5))
            close_price = open_price * (1 + change_rate)
            
            # 음수 방지
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            volume = random.randint(100000, 10000000)
            
            daily_price = {
                'stock_id': stock_id,
                'date': current_date,
                'open_price': round(open_price, 2),
                'high_price': round(high_price, 2),
                'low_price': round(low_price, 2),
                'close_price': round(close_price, 2),
                'adjusted_close': round(close_price, 2),
                'volume': volume,
                'change': round(close_price - open_price, 2),
                'change_rate': round(change_rate * 100, 2)
            }
            result.append(daily_price)
            
            current_price = close_price
        
        current_date += timedelta(days=1)
    
    return result

def generate_sample_market_indices(db, start_date, end_date):
    """샘플 시장 지수 데이터 생성"""
    from datetime import datetime, timedelta
    
    markets = {'KOSPI': 2500, 'KOSDAQ': 800}
    
    for market, base_index in markets.items():
        current_index = base_index
        
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        current_date = start
        while current_date <= end:
            if current_date.weekday() < 5:
                change_rate = random.uniform(-0.02, 0.02)
                
                open_index = current_index
                high_index = open_index * (1 + abs(change_rate) * random.uniform(0.5, 1.2))
                low_index = open_index * (1 - abs(change_rate) * random.uniform(0.5, 1.2))
                close_index = open_index * (1 + change_rate)
                
                high_index = max(high_index, open_index, close_index)
                low_index = min(low_index, open_index, close_index)
                
                volume = random.randint(100000000, 1000000000)
                
                # 기존 데이터 확인
                existing = db.query(MarketIndex).filter_by(
                    market=market,
                    date=current_date
                ).first()
                
                if not existing:
                    market_index = MarketIndex(
                        market=market,
                        date=current_date,
                        open_index=round(open_index, 2),
                        high_index=round(high_index, 2),
                        low_index=round(low_index, 2),
                        close_index=round(close_index, 2),
                        volume=volume,
                        change=round(close_index - open_index, 2),
                        change_rate=round(change_rate * 100, 2)
                    )
                    db.add(market_index)
                
                current_index = close_index
            
            current_date += timedelta(days=1)
    
    db.commit()

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
        
        # 각 종목별로 샘플 데이터 생성
        stocks = db.query(Stock).all()
        base_prices = {
            '005930.KS': 70000,  # 삼성전자
            '000660.KS': 120000, # SK하이닉스
            '035420.KS': 200000, # NAVER
            '035720.KS': 80000,  # 카카오
            '005490.KS': 400000, # POSCO홀딩스
            '293490.KQ': 50000,  # 카카오게임즈
            '259960.KQ': 150000, # 크래프톤
            '068270.KQ': 180000, # 셀트리온
        }
        
        for stock in stocks:
            print(f"처리 중: {stock.name} ({stock.symbol})")
            
            # 샘플 주가 데이터 생성
            sample_data = generate_sample_price_data(stock.stock_id, stock.symbol, start_date, end_date, base_prices)
            if sample_data:
                save_price_data(stock.stock_id, sample_data)
                print(f"  샘플 주가 데이터 {len(sample_data)}개 저장 완료")
                
                # 기술적 지표 계산
                calculate_and_save_technical_indicators(stock.stock_id)
                print(f"  기술적 지표 계산 완료")
            else:
                print(f"  데이터 생성 실패")
        
        # 시장 지수 샘플 데이터 생성
        print("시장 지수 샘플 데이터 생성 중...")
        generate_sample_market_indices(db, start_date, end_date)
        
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