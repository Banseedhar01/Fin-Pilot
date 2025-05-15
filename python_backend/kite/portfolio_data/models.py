from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

@dataclass
class Position:
    trading_symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str
    exchange: str
    instrument_token: int

@dataclass
class Holding:
    trading_symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str
    exchange: str
    instrument_token: int
    t1_quantity: int = 0
    realised_quantity: int = 0
    authorised_quantity: int = 0
    opening_quantity: int = 0
    collateral_quantity: int = 0
    collateral_type: Optional[str] = None
    isin: Optional[str] = None

@dataclass
class Portfolio:
    holdings: List[Holding]
    positions: List[Position]
    last_updated: datetime
    net_value: float
    total_pnl: float

# Pydantic models for API responses
class PositionResponse(BaseModel):
    trading_symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str
    exchange: str
    instrument_token: int

class HoldingResponse(BaseModel):
    trading_symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str
    exchange: str
    instrument_token: int
    t1_quantity: int = 0
    realised_quantity: int = 0
    authorised_quantity: int = 0
    opening_quantity: int = 0
    collateral_quantity: int = 0
    collateral_type: Optional[str] = None
    isin: Optional[str] = None

class PortfolioResponse(BaseModel):
    holdings: List[HoldingResponse]
    positions: List[PositionResponse]
    last_updated: datetime
    net_value: float = Field(..., description="Total portfolio value")
    total_pnl: float = Field(..., description="Total profit and loss") 