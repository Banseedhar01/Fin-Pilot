from kiteconnect import KiteConnect
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from python_backend.core.config import get_settings
from python_backend.core.logger import setup_logger

settings = get_settings()
logger = setup_logger(__name__)

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
    trading_symbol: str = ""
    quantity: int = 0
    average_price: float = 0.0
    last_price: float = 0.0
    pnl: float = 0.0
    product: str = ""
    exchange: str = ""
    instrument_token: int = 0
    t1_quantity: int = 0
    realised_quantity: int = 0
    authorised_quantity: int = 0
    opening_quantity: int = 0
    collateral_quantity: int = 0
    collateral_type: str = ""
    isin: str = ""

@dataclass
class Portfolio:
    holdings: List[Holding]
    positions: List[Position]
    last_updated: datetime
    net_value: float
    total_pnl: float

class KitePortfolioDataManager:
    def __init__(self, access_token: str):
        """
        Initialize the Kite Portfolio Data Manager
        
        Args:
            access_token (str): The access token for Kite API
        """
        self.kite = KiteConnect(api_key=settings.KITE_API_KEY)
        self.kite.set_access_token(access_token)
        self.logger = logger

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return self.kite.access_token is not None

    def _check_authentication(self) -> None:
        """
        Check if the user is authenticated before making API calls
        
        Raises:
            Exception: If user is not authenticated
        """
        if not self.is_authenticated():
            raise Exception("User not authenticated. Please login first.")

    def _convert_holding_to_dataclass(self, holding: Dict[str, Any]) -> Holding:
        """
        Convert a holding dictionary to a Holding dataclass
        
        Args:
            holding (Dict[str, Any]): The holding dictionary from Kite API
            
        Returns:
            Holding: The converted Holding dataclass
        """
        try:
            # Ensure all string fields have default values and proper type conversion
            return Holding(
                trading_symbol=str(holding.get("tradingsymbol", "")),
                quantity=int(holding.get("quantity", 0)),
                average_price=float(holding.get("average_price", 0.0)),
                last_price=float(holding.get("last_price", 0.0)),
                pnl=float(holding.get("pnl", 0.0)),
                product=str(holding.get("product", "")),
                exchange=str(holding.get("exchange", "")),
                instrument_token=int(holding.get("instrument_token", 0)),
                t1_quantity=int(holding.get("t1_quantity", 0)),
                realised_quantity=int(holding.get("realised_quantity", 0)),
                authorised_quantity=int(holding.get("authorised_quantity", 0)),
                opening_quantity=int(holding.get("opening_quantity", 0)),
                collateral_quantity=int(holding.get("collateral_quantity", 0)),
                collateral_type=str(holding.get("collateral_type", "")),  # Ensure it's always a string
                isin=str(holding.get("isin", ""))  # Ensure it's always a string
            )
        except Exception as e:
            self.logger.error(f"Error converting holding to dataclass: {str(e)}")
            raise

    def _convert_position_to_dataclass(self, position: Dict[str, Any]) -> Position:
        """
        Convert a position dictionary to a Position dataclass
        
        Args:
            position (Dict[str, Any]): The position dictionary from Kite API
            
        Returns:
            Position: The converted Position dataclass
        """
        try:
            return Position(
                trading_symbol=str(position.get("tradingsymbol", "")),
                quantity=int(position.get("quantity", 0)),
                average_price=float(position.get("average_price", 0.0)),
                last_price=float(position.get("last_price", 0.0)),
                pnl=float(position.get("pnl", 0.0)),
                product=str(position.get("product", "")),
                exchange=str(position.get("exchange", "")),
                instrument_token=int(position.get("instrument_token", 0))
            )
        except Exception as e:
            self.logger.error(f"Error converting position to dataclass: {str(e)}")
            raise

    def fetch_portfolio(self) -> Portfolio:
        """
        Fetch the complete portfolio data from Kite
        
        Returns:
            Portfolio: The complete portfolio data
            
        Raises:
            Exception: If there's an error fetching the portfolio
        """
        try:
            self._check_authentication()
            
            # Fetch holdings and positions
            holdings = self.get_holdings()
            positions = self.get_positions()
            
            # Calculate total values
            total_holdings_value = sum(holding.quantity * holding.last_price for holding in holdings)
            total_positions_value = sum(position.quantity * position.last_price for position in positions)
            net_value = total_holdings_value + total_positions_value
            
            total_pnl = sum(holding.pnl for holding in holdings) + sum(position.pnl for position in positions)
            
            return Portfolio(
                holdings=holdings,
                positions=positions,
                last_updated=datetime.now(),
                net_value=net_value,
                total_pnl=total_pnl
            )
        except Exception as e:
            self.logger.error(f"Error fetching portfolio: {str(e)}")
            raise

    def get_holdings(self) -> List[Holding]:
        """
        Fetch only holdings from Kite
        
        Returns:
            List[Holding]: List of holdings
            
        Raises:
            Exception: If there's an error fetching holdings
        """
        try:
            self._check_authentication()
            holdings_data = self.kite.holdings()
            if not isinstance(holdings_data, list):
                self.logger.error(f"Invalid holdings data format: {holdings_data}")
                raise Exception("Invalid holdings data format")
            return [self._convert_holding_to_dataclass(holding) for holding in holdings_data]
        except Exception as e:
            self.logger.error(f"Error fetching holdings: {str(e)}")
            raise

    def get_positions(self) -> List[Position]:
        """
        Fetch only positions from Kite
        
        Returns:
            List[Position]: List of positions
            
        Raises:
            Exception: If there's an error fetching positions
        """
        try:
            self._check_authentication()
            positions_data = self.kite.positions()
            
            # Handle different response formats
            if isinstance(positions_data, dict):
                # If positions are in a dictionary format
                positions_list = positions_data.get('net', [])
                if not isinstance(positions_list, list):
                    self.logger.error(f"Invalid positions data format: {positions_data}")
                    raise Exception("Invalid positions data format")
                return [self._convert_position_to_dataclass(position) for position in positions_list]
            elif isinstance(positions_data, list):
                # If positions are directly in a list format
                return [self._convert_position_to_dataclass(position) for position in positions_data]
            else:
                self.logger.error(f"Invalid positions data format: {positions_data}")
                raise Exception("Invalid positions data format")
        except Exception as e:
            self.logger.error(f"Error fetching positions: {str(e)}")
            raise

    def get_margins(self) -> Dict[str, Any]:
        """
        Fetch margin information from Kite
        
        Returns:
            Dict[str, Any]: Margin information
            
        Raises:
            Exception: If there's an error fetching margins
        """
        try:
            self._check_authentication()
            return self.kite.margins()
        except Exception as e:
            self.logger.error(f"Error fetching margins: {str(e)}")
            raise

    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all orders from Kite
        
        Returns:
            List[Dict[str, Any]]: List of orders
            
        Raises:
            Exception: If there's an error fetching orders
        """
        try:
            self._check_authentication()
            return self.kite.orders()
        except Exception as e:
            self.logger.error(f"Error fetching orders: {str(e)}")
            raise

    def get_trades(self) -> List[Dict[str, Any]]:
        """
        Fetch all trades from Kite
        
        Returns:
            List[Dict[str, Any]]: List of trades
            
        Raises:
            Exception: If there's an error fetching trades
        """
        try:
            self._check_authentication()
            return self.kite.trades()
        except Exception as e:
            self.logger.error(f"Error fetching trades: {str(e)}")
            raise 