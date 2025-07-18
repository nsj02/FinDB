# models.py - TimescaleDB 기반 데이터베이스 모델

import os
import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean, Text, DateTime, UniqueConstraint, Index, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func, text
import ta
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import MACD, SMAIndicator
from datetime import datetime, timedelta
import time
import logging
import concurrent.futures
from tqdm import tqdm
from pykrx import stock

# 데이터베이스 연결 설정 (환경변수 사용)
DB_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/finance_db')
engine = create_engine(DB_URI, echo=False, pool_size=20, max_overflow=0)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Stock(Base):
    __tablename__ = 'stocks'
    
    stock_id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    krx_code = Column(String(20), index=True)
    name = Column(String(100), nullable=False, index=True)
    market = Column(String(20), index=True)
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    listing_date = Column(Date)
    delisting_date = Column(Date)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    daily_prices = relationship("DailyPrice", back_populates="stock", cascade="all, delete-orphan")
    technical_indicators = relationship("TechnicalIndicator", back_populates="stock", cascade="all, delete-orphan")

class DailyPrice(Base):
    __tablename__ = 'daily_prices'
    
    price_id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.stock_id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    adjusted_close = Column(Float)
    volume = Column(Integer)
    change = Column(Float)
    change_rate = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    stock = relationship("Stock", back_populates="daily_prices")
    
    # 인덱스 추가
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uix_stock_date'),
        Index('ix_daily_prices_date', 'date'),
    )

class TechnicalIndicator(Base):
    __tablename__ = 'technical_indicators'
    
    indicator_id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.stock_id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    
    # 이동평균선
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    ma120 = Column(Float)
    
    # 볼린저 밴드
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_width = Column(Float)
    
    # RSI
    rsi = Column(Float)
    
    # MACD
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    
    # 볼륨 관련
    volume_ma20 = Column(Float)
    volume_ratio = Column(Float)
    
    # 캔들 패턴
    is_doji = Column(Boolean)
    is_hammer = Column(Boolean)
    
    # 시그널
    golden_cross = Column(Boolean)
    death_cross = Column(Boolean)
    bb_upper_touch = Column(Boolean)
    bb_lower_touch = Column(Boolean)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    stock = relationship("Stock", back_populates="technical_indicators")
    
    # 인덱스 추가
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uix_stock_indicator_date'),
        Index('ix_tech_indicators_date', 'date'),
        Index('ix_tech_indicators_rsi', 'rsi'),
        Index('ix_tech_indicators_volume_ratio', 'volume_ratio'),
    )

class MarketIndex(Base):
    __tablename__ = 'market_indices'
    
    index_id = Column(Integer, primary_key=True)
    market = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False)
    open_index = Column(Float)
    high_index = Column(Float)
    low_index = Column(Float)
    close_index = Column(Float)
    volume = Column(Integer)
    change = Column(Float)
    change_rate = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 인덱스 추가
    __table_args__ = (
        UniqueConstraint('market', 'date', name='uix_market_date'),
        Index('ix_market_indices_date', 'date'),
    )

class MarketStat(Base):
    __tablename__ = 'market_stats'
    
    stat_id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    market = Column(String(20), nullable=False)
    rising_stocks = Column(Integer)
    falling_stocks = Column(Integer)
    unchanged_stocks = Column(Integer)
    total_stocks = Column(Integer)
    # 오류 해결: BigInteger와 Float 사용
    total_volume = Column(BigInteger)  # Integer -> BigInteger로 변경
    total_value = Column(Float)        # 이미 Float이지만 명시적으로 유지
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 인덱스 추가
    __table_args__ = (
        UniqueConstraint('market', 'date', name='uix_market_stat_date'),
        Index('ix_market_stats_date', 'date'),
    )

# TimescaleDB 하이퍼테이블 생성 함수
def create_hypertables():
    """TimescaleDB 하이퍼테이블을 생성합니다."""
    session = Session()
    try:
        # daily_prices 테이블을 하이퍼테이블로 변환
        session.execute(text("""
            SELECT create_hypertable('daily_prices', 'date', 
                                   chunk_time_interval => INTERVAL '1 month',
                                   if_not_exists => TRUE);
        """))
        logger.info("daily_prices 하이퍼테이블 생성 완료")
        
        # technical_indicators 테이블을 하이퍼테이블로 변환
        session.execute(text("""
            SELECT create_hypertable('technical_indicators', 'date', 
                                   chunk_time_interval => INTERVAL '1 month',
                                   if_not_exists => TRUE);
        """))
        logger.info("technical_indicators 하이퍼테이블 생성 완료")
        
        # market_indices 테이블을 하이퍼테이블로 변환
        session.execute(text("""
            SELECT create_hypertable('market_indices', 'date', 
                                   chunk_time_interval => INTERVAL '1 month',
                                   if_not_exists => TRUE);
        """))
        logger.info("market_indices 하이퍼테이블 생성 완료")
        
        # market_stats 테이블을 하이퍼테이블로 변환
        session.execute(text("""
            SELECT create_hypertable('market_stats', 'date', 
                                   chunk_time_interval => INTERVAL '1 month',
                                   if_not_exists => TRUE);
        """))
        logger.info("market_stats 하이퍼테이블 생성 완료")
        
        # 압축 정책 설정 (1개월 이상된 데이터는 압축)
        session.execute(text("""
            SELECT add_compression_policy('daily_prices', INTERVAL '1 month');
        """))
        
        session.execute(text("""
            SELECT add_compression_policy('technical_indicators', INTERVAL '1 month');
        """))
        
        session.execute(text("""
            SELECT add_compression_policy('market_indices', INTERVAL '1 month');
        """))
        
        session.execute(text("""
            SELECT add_compression_policy('market_stats', INTERVAL '1 month');
        """))
        
        logger.info("데이터 압축 정책 설정 완료")
        
        session.commit()
        logger.info("TimescaleDB 하이퍼테이블 설정이 완료되었습니다.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"하이퍼테이블 생성 중 오류 발생: {e}")
        # 하이퍼테이블 생성 실패는 치명적이지 않으므로 계속 진행
        pass
    finally:
        session.close()

# 데이터베이스 초기화 함수
def init_db():
    """데이터베이스 테이블을 생성하고 TimescaleDB 하이퍼테이블을 설정합니다."""
    Base.metadata.create_all(engine)
    logger.info("데이터베이스 테이블이 생성되었습니다.")
    
    # TimescaleDB 하이퍼테이블 생성
    create_hypertables()
    
    # 데이터 보존 정책 설정 (3년 이상된 데이터는 자동 삭제)
    session = Session()
    try:
        session.execute(text("""
            SELECT add_retention_policy('daily_prices', INTERVAL '3 years');
        """))
        
        session.execute(text("""
            SELECT add_retention_policy('technical_indicators', INTERVAL '3 years');
        """))
        
        session.execute(text("""
            SELECT add_retention_policy('market_indices', INTERVAL '3 years');
        """))
        
        session.execute(text("""
            SELECT add_retention_policy('market_stats', INTERVAL '3 years');
        """))
        
        session.commit()
        logger.info("데이터 보존 정책 설정 완료 (3년)")
        
    except Exception as e:
        session.rollback()
        logger.warning(f"데이터 보존 정책 설정 중 오류 발생: {e}")
    finally:
        session.close()