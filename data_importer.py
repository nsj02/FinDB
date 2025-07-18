# data_importer.py - 수정된 데이터 수집 및 저장 로직

import os
import pandas as pd
import numpy as np
import yfinance as yf
from models import *
from datetime import datetime, timedelta
import logging
import concurrent.futures
from tqdm import tqdm
from pykrx import stock

logger = logging.getLogger(__name__)

# pykrx를 사용하여 한국 주식 종목 목록 가져오기
def get_korean_stock_symbols():
    try:
        today = datetime.now().strftime('%Y%m%d')
        
        # KOSPI 종목 가져오기
        kospi_tickers = stock.get_market_ticker_list(today, market="KOSPI")
        kospi_symbols = []
        
        for ticker in kospi_tickers:
            name = stock.get_market_ticker_name(ticker)
            kospi_symbols.append({
                'symbol': f'{ticker}.KS',
                'krx_code': ticker,
                'name': name,
                'market': 'KOSPI'
            })
        
        # KOSDAQ 종목 가져오기
        kosdaq_tickers = stock.get_market_ticker_list(today, market="KOSDAQ")
        kosdaq_symbols = []
        
        for ticker in kosdaq_tickers:
            name = stock.get_market_ticker_name(ticker)
            kosdaq_symbols.append({
                'symbol': f'{ticker}.KQ',
                'krx_code': ticker,
                'name': name,
                'market': 'KOSDAQ'
            })
        
        logger.info(f"종목 정보 가져오기 완료: KOSPI {len(kospi_symbols)}개, KOSDAQ {len(kosdaq_symbols)}개")
        return kospi_symbols + kosdaq_symbols
    except Exception as e:
        logger.error(f"종목 정보 가져오기 오류: {e}")
        # 샘플 데이터 반환
        return [
            {'symbol': '005930.KS', 'krx_code': '005930', 'name': '삼성전자', 'market': 'KOSPI'},
            {'symbol': '000660.KS', 'krx_code': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI'},
            {'symbol': '035420.KS', 'krx_code': '035420', 'name': 'NAVER', 'market': 'KOSPI'}
        ]

# 주식 기본 정보 저장
def save_stock_info(symbols):
    session = Session()
    try:
        for symbol_info in tqdm(symbols, desc="종목 정보 저장"):
            symbol = symbol_info['symbol']
            krx_code = symbol_info['krx_code']
            name = symbol_info['name']
            market = symbol_info['market']
            
            # 이미 있는지 확인
            existing_stock = session.query(Stock).filter_by(symbol=symbol).first()
            
            if existing_stock:
                continue
            
            # 야후 파이낸스에서 추가 정보 가져오기
            try:
                stock_info = yf.Ticker(symbol).info
                sector = stock_info.get('sector', '')
                industry = stock_info.get('industry', '')
                description = stock_info.get('longBusinessSummary', '')
            except Exception as e:
                sector = ''
                industry = ''
                description = ''
            
            # 데이터베이스에 저장
            new_stock = Stock(
                symbol=symbol,
                krx_code=krx_code,
                name=name,
                market=market,
                sector=sector,
                industry=industry,
                description=description,
                is_active=True
            )
            
            session.add(new_stock)
        
        session.commit()
        logger.info(f"종목 정보 저장 완료")
    except Exception as e:
        session.rollback()
        logger.error(f"종목 정보 저장 오류: {e}")
    finally:
        session.close()

def fetch_stock_price(stock_id, symbol, start_date, end_date):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
        
        if df is None or df.empty:
            return []

        # Series인 경우 DataFrame으로 변환
        if isinstance(df, pd.Series):
            df = df.to_frame().T

        df.reset_index(inplace=True)
        
        # 필요한 열 확인
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return []
        
        # 열 이름 변경
        rename_map = {
            'Date': 'date',
            'Open': 'open_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Close': 'close_price',
            'Volume': 'volume'
        }
        
        if 'Adj Close' in df.columns:
            rename_map['Adj Close'] = 'adjusted_close'
        
        df.rename(columns=rename_map, inplace=True)
        
        if 'adjusted_close' not in df.columns:
            df['adjusted_close'] = df['close_price']
        
        # 변화율 계산
        df['change'] = df['adjusted_close'].diff()
        df['change_rate'] = df['adjusted_close'].pct_change() * 100
        
        df.fillna(0, inplace=True)
        
        # 결과 포맷팅
        result = []
        for _, row in df.iterrows():
            try:
                if isinstance(row['date'], pd.Timestamp):
                    date_value = row['date'].date()
                else:
                    continue
                
                daily_price = {
                    'stock_id': stock_id,
                    'date': date_value,
                    'open_price': float(row['open_price']),
                    'high_price': float(row['high_price']),
                    'low_price': float(row['low_price']),
                    'close_price': float(row['close_price']),
                    'adjusted_close': float(row['adjusted_close']),
                    'volume': int(row['volume']),
                    'change': float(row['change']),
                    'change_rate': float(row['change_rate'])
                }
                result.append(daily_price)
            except Exception as e:
                continue
        
        return result
    except Exception as e:
        logger.error(f"가격 데이터 가져오기 오류 ({symbol}): {e}")
        return []

# 시장 지수 데이터 가져오기 및 저장 (오류 수정)
def fetch_and_save_market_indices(db, start_date, end_date):
    indices = {
        'KOSPI': '^KS11',
        'KOSDAQ': '^KQ11'
    }
    
    try:
        for market_name, symbol in indices.items():
            logger.info(f"{market_name} 지수 데이터 가져오는 중...")
            
            # 야후 파이낸스에서 데이터 가져오기 (auto_adjust=False 명시)
            df = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=False)
            
            if df.empty:
                logger.warning(f"{market_name} 지수 데이터가 없습니다.")
                continue
            
            # MultiIndex 컬럼 처리 (yfinance 최신 버전 대응)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            # Series인 경우 DataFrame으로 변환
            if isinstance(df, pd.Series):
                df = df.to_frame().T
            
            df.reset_index(inplace=True)
            df.rename(columns={
                'Date': 'date',
                'Open': 'open_index',
                'High': 'high_index',
                'Low': 'low_index',
                'Close': 'close_index',
                'Volume': 'volume'
            }, inplace=True)
            
            # 변화율 계산
            df['change'] = df['close_index'].diff()
            df['change_rate'] = df['close_index'].pct_change() * 100
            df.fillna(0, inplace=True)
            
            # 저장
            for idx, row in df.iterrows():
                try:
                    # 날짜 처리 수정 - DataFrame의 인덱스를 사용
                    if isinstance(idx, pd.Timestamp):
                        date_value = idx.date()
                    elif hasattr(idx, 'date'):
                        date_value = idx.date()
                    else:
                        # 인덱스가 아닌 경우 row에서 추출
                        date_col = row['date']
                        if isinstance(date_col, pd.Timestamp):
                            date_value = date_col.date()
                        elif hasattr(date_col, 'date'):
                            date_value = date_col.date()
                        else:
                            date_value = pd.to_datetime(date_col).date()
                    
                    # 이미 있는지 확인
                    existing_index = db.query(MarketIndex).filter_by(
                        market=market_name,
                        date=date_value
                    ).first()
                    
                    if existing_index:
                        # 기존 데이터 업데이트
                        existing_index.open_index = row['open_index']
                        existing_index.high_index = row['high_index']
                        existing_index.low_index = row['low_index']
                        existing_index.close_index = row['close_index']
                        existing_index.volume = row['volume']
                        existing_index.change = row['change']
                        existing_index.change_rate = row['change_rate']
                    else:
                        # 새 데이터 추가
                        new_index = MarketIndex(
                            market=market_name,
                            date=date_value,
                            open_index=row['open_index'],
                            high_index=row['high_index'],
                            low_index=row['low_index'],
                            close_index=row['close_index'],
                            volume=row['volume'],
                            change=row['change'],
                            change_rate=row['change_rate']
                        )
                        db.add(new_index)
                except Exception as e:
                    logger.error(f"시장 지수 행 처리 오류: {e}")
                    continue
            
            logger.info(f"{market_name} 지수 데이터 저장 완료")
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"시장 지수 데이터 저장 오류: {e}")
        return False

# 주가 데이터 저장
def save_price_data(stock_id, price_data):
    session = Session()
    try:
        for data in price_data:
            existing_price = session.query(DailyPrice).filter_by(
                stock_id=stock_id,
                date=data['date']
            ).first()
            
            if existing_price:
                for key, value in data.items():
                    if key != 'stock_id' and key != 'date':
                        setattr(existing_price, key, value)
            else:
                new_price = DailyPrice(**data)
                session.add(new_price)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"가격 데이터 저장 오류: {e}")
        return False
    finally:
        session.close()

# 기술적 지표 계산 및 저장
def calculate_and_save_technical_indicators(stock_id):
    session = Session()
    try:
        price_data = session.query(DailyPrice).filter_by(stock_id=stock_id).order_by(DailyPrice.date).all()
        
        if not price_data:
            return False
        
        # 데이터프레임으로 변환
        df = pd.DataFrame([{
            'date': p.date,
            'open': p.open_price,
            'high': p.high_price,
            'low': p.low_price,
            'close': p.adjusted_close,
            'volume': p.volume
        } for p in price_data])
        
        # 이동평균선 계산
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        df['ma120'] = df['close'].rolling(window=120).mean()
        
        # 볼린저 밴드
        bb_indicator = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb_indicator.bollinger_hband()
        df['bb_middle'] = bb_indicator.bollinger_mavg()
        df['bb_lower'] = bb_indicator.bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # RSI
        rsi_indicator = RSIIndicator(close=df['close'], window=14)
        df['rsi'] = rsi_indicator.rsi()
        
        # MACD
        macd_indicator = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
        df['macd'] = macd_indicator.macd()
        df['macd_signal'] = macd_indicator.macd_signal()
        df['macd_hist'] = macd_indicator.macd_diff()
        
        # 볼륨 관련
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20'] * 100
        
        # 캔들 패턴
        df['body_size'] = abs(df['close'] - df['open'])
        df['shadow_upper'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['shadow_lower'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_doji'] = (df['body_size'] / (df['high'] - df['low'] + 0.001) < 0.1)
        df['is_hammer'] = ((df['shadow_lower'] > 2 * df['body_size']) & 
                          (df['shadow_upper'] < df['body_size']) & 
                          (df['body_size'] > 0))
        
        # 시그널
        df['ma5_prev'] = df['ma5'].shift(1)
        df['ma20_prev'] = df['ma20'].shift(1)
        df['golden_cross'] = (df['ma5'] > df['ma20']) & (df['ma5_prev'] <= df['ma20_prev'])
        df['death_cross'] = (df['ma5'] < df['ma20']) & (df['ma5_prev'] >= df['ma20_prev'])
        
        # 볼린저 밴드 터치
        df['bb_upper_touch'] = (df['high'] >= df['bb_upper'])
        df['bb_lower_touch'] = (df['low'] <= df['bb_lower'])
        
        df.fillna(0, inplace=True)
        
        # 기존 지표 삭제
        session.query(TechnicalIndicator).filter_by(stock_id=stock_id).delete()
        
        # 새 지표 저장
        for _, row in df.iterrows():
            if pd.isna(row['date']):
                continue
                
            new_indicator = TechnicalIndicator(
                stock_id=stock_id,
                date=row['date'],
                ma5=row['ma5'],
                ma10=row['ma10'],
                ma20=row['ma20'],
                ma60=row['ma60'],
                ma120=row['ma120'],
                bb_upper=row['bb_upper'],
                bb_middle=row['bb_middle'],
                bb_lower=row['bb_lower'],
                bb_width=row['bb_width'],
                rsi=row['rsi'],
                macd=row['macd'],
                macd_signal=row['macd_signal'],
                macd_hist=row['macd_hist'],
                volume_ma20=row['volume_ma20'],
                volume_ratio=row['volume_ratio'],
                is_doji=row['is_doji'],
                is_hammer=row['is_hammer'],
                golden_cross=row['golden_cross'],
                death_cross=row['death_cross'],
                bb_upper_touch=row['bb_upper_touch'],
                bb_lower_touch=row['bb_lower_touch']
            )
            session.add(new_indicator)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"기술적 지표 계산 오류 (종목 ID: {stock_id}): {e}")
        return False
    finally:
        session.close()

# 시장 통계 계산 및 저장
def calculate_market_stats(db):
    try:
        # 모든 날짜 가져오기
        dates = [date[0] for date in db.query(DailyPrice.date).distinct().all()]
        
        for date in tqdm(dates, desc="시장 통계 계산"):
            # KOSPI 통계
            kospi_stats = calculate_market_stat_for_date(db, date, 'KOSPI')
            # KOSDAQ 통계
            kosdaq_stats = calculate_market_stat_for_date(db, date, 'KOSDAQ')
            
            # 전체 시장 통계
            total_stats = {
                'date': date,
                'market': 'ALL',
                'rising_stocks': kospi_stats['rising_stocks'] + kosdaq_stats['rising_stocks'],
                'falling_stocks': kospi_stats['falling_stocks'] + kosdaq_stats['falling_stocks'],
                'unchanged_stocks': kospi_stats['unchanged_stocks'] + kosdaq_stats['unchanged_stocks'],
                'total_stocks': kospi_stats['total_stocks'] + kosdaq_stats['total_stocks'],
                'total_volume': kospi_stats['total_volume'] + kosdaq_stats['total_volume'],
                'total_value': kospi_stats['total_value'] + kosdaq_stats['total_value']
            }
            
            # 저장
            save_market_stat(db, kospi_stats)
            save_market_stat(db, kosdaq_stats)
            save_market_stat(db, total_stats)
        
        db.commit()
        logger.info("시장 통계 계산 및 저장 완료")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"시장 통계 계산 오류: {e}")
        return False

# 특정 날짜, 특정 시장에 대한 통계 계산
def calculate_market_stat_for_date(db, date, market):
    stocks = db.query(Stock).filter_by(market=market).all()
    stock_ids = [stock.stock_id for stock in stocks]
    
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_id.in_(stock_ids),
        DailyPrice.date == date
    ).all()
    
    # 통계 계산
    rising_stocks = sum(1 for p in prices if p.change > 0)
    falling_stocks = sum(1 for p in prices if p.change < 0)
    unchanged_stocks = sum(1 for p in prices if p.change == 0)
    total_stocks = len(prices)
    total_volume = sum(p.volume for p in prices)
    total_value = sum(p.volume * p.close_price for p in prices)
    
    return {
        'date': date,
        'market': market,
        'rising_stocks': rising_stocks,
        'falling_stocks': falling_stocks,
        'unchanged_stocks': unchanged_stocks,
        'total_stocks': total_stocks,
        'total_volume': total_volume,
        'total_value': total_value
    }

# 시장 통계 저장
def save_market_stat(db, stat_data):
    existing_stat = db.query(MarketStat).filter_by(
        market=stat_data['market'],
        date=stat_data['date']
    ).first()
    
    if existing_stat:
        for key, value in stat_data.items():
            if key != 'market' and key != 'date':
                setattr(existing_stat, key, value)
    else:
        new_stat = MarketStat(**stat_data)
        db.add(new_stat)

# 주식 데이터 가져오기 (병렬 처리)
def fetch_stock_data(start_date, end_date, max_workers=10):
    session = Session()
    try:
        stocks = session.query(Stock).all()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for stock in stocks:
                futures.append(
                    executor.submit(
                        process_stock_data,
                        stock.stock_id,
                        stock.symbol,
                        stock.name,
                        start_date,
                        end_date
                    )
                )
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="종목 데이터 처리"):
                try:
                    result = future.result()
                    logger.debug(f"종목 처리 완료: {result}")
                except Exception as e:
                    logger.error(f"종목 처리 오류: {e}")
        
        logger.info("모든 종목 데이터 처리 완료")
    finally:
        session.close()

# 단일 종목 데이터 처리
def process_stock_data(stock_id, symbol, name, start_date, end_date):
    price_data = fetch_stock_price(stock_id, symbol, start_date, end_date)
    
    if not price_data:
        return f"{name}: 데이터 없음"
    
    save_result = save_price_data(stock_id, price_data)
    
    if not save_result:
        return f"{name}: 저장 실패"
    
    indicator_result = calculate_and_save_technical_indicators(stock_id)
    
    return f"{name}: 처리 완료 ({len(price_data)}개 데이터)"

# 초기 데이터베이스 구축
def build_initial_database(db, years=3):
    today = datetime.now().date()
    start_date = (today - timedelta(days=365 * years)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    logger.info(f"초기 데이터베이스 구축 시작 (기간: {start_date} ~ {end_date})")
    
    # 종목 정보 저장
    symbols = get_korean_stock_symbols()
    save_stock_info(symbols)
    
    # 주가 데이터 가져오기
    fetch_stock_data(start_date, end_date)
    
    # 시장 지수 가져오기
    fetch_and_save_market_indices(db, start_date, end_date)
    
    # 시장 통계 계산
    calculate_market_stats(db)
    
    logger.info("초기 데이터베이스 구축 완료")

# 일일 데이터 업데이트
def update_daily_data(db, days=2):
    today = datetime.now().date()
    start_date = (today - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    logger.info(f"일일 데이터 업데이트 시작 (기간: {start_date} ~ {end_date})")
    
    # 종목 정보 업데이트
    symbols = get_korean_stock_symbols()
    save_stock_info(symbols)
    
    # 주가 데이터 업데이트
    fetch_stock_data(start_date, end_date)
    
    # 시장 지수 업데이트
    fetch_and_save_market_indices(db, start_date, end_date)
    
    logger.info("일일 데이터 업데이트 완료")

# 전체 기술적 지표 재계산
def update_full_technical_indicators(db):
    logger.info("기술적 지표 전체 재계산 시작")
    
    stocks = db.query(Stock).all()
    
    for stock in tqdm(stocks, desc="기술적 지표 재계산"):
        calculate_and_save_technical_indicators(stock.stock_id)
    
    logger.info("기술적 지표 전체 재계산 완료")

# 시장 통계 재계산
def update_market_stats(db):
    logger.info("시장 통계 재계산 시작")
    calculate_market_stats(db)
    logger.info("시장 통계 재계산 완료")