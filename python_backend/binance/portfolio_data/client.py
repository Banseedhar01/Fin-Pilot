from typing import Dict, List, Any
import time
import hmac
import hashlib
import requests
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from ...core.logger import setup_logger
from ...core.config import get_settings

settings = get_settings()
logger = setup_logger(__name__)

class BinancePortfolioClient:
    """Client for fetching Binance portfolio data"""
    
    def __init__(self):
        """Initialize Binance client with API credentials"""
        self.client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
        logger.info("Binance portfolio client initialized")
    
    def fetch_buy_trades(self, symbol: str) -> Dict[str, Any]:
        """Fetch buy trades for a specific symbol to determine average buy price"""
        try:
            # Format the symbol for API call if needed
            trading_pair = symbol
            if not symbol.endswith('USDT'):
                trading_pair = f"{symbol}USDT"
                
            # Define query parameters
            timestamp = int(time.time() * 1000)
            query_string = f"symbol={trading_pair}&timestamp={timestamp}"
            
            # Generate signature
            signature = hmac.new(
                settings.BINANCE_API_SECRET.encode(), 
                query_string.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            # Define headers and URL
            headers = {'X-MBX-APIKEY': settings.BINANCE_API_KEY}
            url = f"https://api.binance.com/api/v3/myTrades?{query_string}&signature={signature}"
            
            # Make API request
            logger.info(f"Fetching trade history for {trading_pair}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                trades = response.json()
                
                # Filter for buy trades only
                buy_trades = [t for t in trades if t.get('isBuyer', False)]
                
                if not buy_trades:
                    logger.info(f"No buy trades found for {trading_pair}")
                    return {
                        'avg_buy_price': None,
                        'first_buy_time': None,
                        'last_buy_time': None,
                        'total_qty_bought': 0
                    }
                
                # Calculate total quantity and cost
                total_qty = sum(float(t['qty']) for t in buy_trades)
                total_cost = sum(float(t['qty']) * float(t['price']) for t in buy_trades)
                
                # Calculate average buy price
                avg_buy_price = total_cost / total_qty if total_qty > 0 else 0
                
                # Get first and last buy times
                buy_times = [int(t['time']) for t in buy_trades]
                first_buy_time = min(buy_times) if buy_times else None
                last_buy_time = max(buy_times) if buy_times else None
                
                logger.info(f"Calculated average buy price for {trading_pair}: {avg_buy_price}")
                
                return {
                    'avg_buy_price': avg_buy_price,
                    'first_buy_time': first_buy_time,
                    'last_buy_time': last_buy_time,
                    'total_qty_bought': total_qty
                }
            else:
                logger.error(f"Error fetching trades for {trading_pair}: {response.text}")
                return {
                    'avg_buy_price': None,
                    'first_buy_time': None,
                    'last_buy_time': None,
                    'total_qty_bought': 0
                }
                
        except Exception as e:
            logger.error(f"Error in fetch_buy_trades for {symbol}: {e}")
            return {
                'avg_buy_price': None,
                'first_buy_time': None,
                'last_buy_time': None,
                'total_qty_bought': 0
            }
    
    def fetch_spot_holdings(self) -> Dict[str, Dict[str, Any]]:
        """Fetch spot trading holdings"""
        try:
            account = self.client.get_account()
            holdings = {}
            for balance in account['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    # Get the current price of the asset in USD
                    symbol = f"{balance['asset']}USDT"
                    try:
                        ticker = self.client.get_symbol_ticker(symbol=symbol)
                        price_usd = float(ticker['price'])
                    except:
                        # If the asset doesn't have a direct USDT pair, try to get it through BTC
                        try:
                            btc_ticker = self.client.get_symbol_ticker(symbol=f"{balance['asset']}BTC")
                            btc_price = float(btc_ticker['price'])
                            usdt_ticker = self.client.get_symbol_ticker(symbol="BTCUSDT")
                            usdt_price = float(usdt_ticker['price'])
                            price_usd = btc_price * usdt_price
                        except:
                            # If we can't get the price, use 0
                            price_usd = 0
                    
                    # Calculate USD values
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    usd_value = total * price_usd
                    
                    # Get buy price information
                    buy_data = self.fetch_buy_trades(balance['asset'])
                    avg_buy_price = buy_data.get('avg_buy_price')
                    
                    # Calculate PNL if buy price is available
                    pnl = None
                    pnl_percentage = None
                    if avg_buy_price is not None and avg_buy_price > 0:
                        pnl = (price_usd - avg_buy_price) * total
                        pnl_percentage = ((price_usd / avg_buy_price) - 1) * 100
                    
                    holdings[balance['asset']] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'total_usd': usd_value,
                        'type': 'spot',
                        'price_usd': price_usd,
                        'avg_buy_price': avg_buy_price,
                        'pnl': pnl,
                        'pnl_percentage': pnl_percentage,
                        'first_buy_time': buy_data.get('first_buy_time'),
                        'last_buy_time': buy_data.get('last_buy_time')
                    }
            
            logger.info(f"Successfully fetched {len(holdings)} spot holdings")
            return holdings
            
        except Exception as e:
            logger.error(f"Error fetching spot holdings: {str(e)}")
            raise
    
    def fetch_margin_holdings(self) -> Dict[str, Dict[str, Any]]:
        """Fetch margin trading holdings"""
        try:
            margin_account = self.client.get_margin_account()
            holdings = {}
            for asset in margin_account['userAssets']:
                if float(asset['netAsset']) > 0:
                    # Get the current price of the asset in USD
                    symbol = f"{asset['asset']}USDT"
                    try:
                        ticker = self.client.get_symbol_ticker(symbol=symbol)
                        price_usd = float(ticker['price'])
                    except:
                        # If the asset doesn't have a direct USDT pair, try to get it through BTC
                        try:
                            btc_ticker = self.client.get_symbol_ticker(symbol=f"{asset['asset']}BTC")
                            btc_price = float(btc_ticker['price'])
                            usdt_ticker = self.client.get_symbol_ticker(symbol="BTCUSDT")
                            usdt_price = float(usdt_ticker['price'])
                            price_usd = btc_price * usdt_price
                        except:
                            # If we can't get the price, use 0
                            price_usd = 0
                    
                    # Calculate USD value
                    net_asset = float(asset['netAsset'])
                    usd_value = net_asset * price_usd
                    
                    # Get buy price information
                    buy_data = self.fetch_buy_trades(asset['asset'])
                    avg_buy_price = buy_data.get('avg_buy_price')
                    
                    # Calculate PNL if buy price is available
                    pnl = None
                    pnl_percentage = None
                    if avg_buy_price is not None and avg_buy_price > 0:
                        pnl = (price_usd - avg_buy_price) * net_asset
                        pnl_percentage = ((price_usd / avg_buy_price) - 1) * 100
                    
                    holdings[asset['asset']] = {
                        'net_asset': net_asset,
                        'net_asset_usd': usd_value,
                        'borrowed': float(asset['borrowed']),
                        'type': 'spot_cross_margin',
                        'price_usd': price_usd,
                        'avg_buy_price': avg_buy_price,
                        'pnl': pnl,
                        'pnl_percentage': pnl_percentage,
                        'first_buy_time': buy_data.get('first_buy_time'),
                        'last_buy_time': buy_data.get('last_buy_time')
                    }
            
            logger.info(f"Successfully fetched {len(holdings)} margin holdings")
            return holdings
            
        except Exception as e:
            logger.error(f"Error fetching margin holdings: {str(e)}")
            raise
    
    def fetch_futures_holdings(self) -> Dict[str, Dict[str, Any]]:
        """Fetch futures trading holdings"""
        try:
            futures_account = self.client.futures_account()
            holdings = {}
            for position in futures_account['positions']:
                if float(position['positionAmt']) != 0:
                    # Get the current price of the asset in USD
                    symbol = position['symbol']
                    try:
                        ticker = self.client.futures_symbol_ticker(symbol=symbol)
                        price_usd = float(ticker['price'])
                    except:
                        # If we can't get the price, use 0
                        price_usd = 0
                    
                    # Calculate USD values
                    amount = float(position['positionAmt'])
                    entry_price = float(position['entryPrice'])
                    unrealized_pnl = float(position.get('unRealizedProfit', 0.0))
                    leverage = int(position.get('leverage', 1))
                    
                    # Calculate the USD value of the position
                    usd_value = abs(amount) * price_usd
                    
                    holdings[position['symbol']] = {
                        'amount': amount,
                        'entry_price': entry_price,
                        'current_price': price_usd,
                        'unrealized_pnl': unrealized_pnl,
                        'unrealized_pnl_usd': unrealized_pnl,  # Already in USD
                        'leverage': leverage,
                        'usd_value': usd_value,
                        'type': 'futures'
                    }
            
            logger.info(f"Successfully fetched {len(holdings)} futures holdings")
            return holdings
            
        except Exception as e:
            logger.error(f"Error fetching futures holdings: {str(e)}")
            raise
    
    def fetch_24hr_changes(self, symbols: List[str] = None) -> Dict[str, Dict[str, float]]:
        """Fetch 24-hour price changes for given symbols"""
        try:
            if not symbols:
                return {}
                
            changes_data = {}
            
            for symbol in symbols:
                # Remove any suffix like _spot or _margin to get the base symbol
                base_symbol = symbol.split('_')[0] if '_' in symbol else symbol
                
                # Skip USDT as it's the quote currency
                if base_symbol == 'USDT':
                    continue
                    
                # Format the symbol for the API call
                # If the symbol already contains USDT (like BTCUSDT), use it directly
                if 'USDT' in base_symbol:
                    trading_pair = base_symbol
                else:
                    trading_pair = f"{base_symbol}USDT"
                
                try:
                    # Call the 24hr ticker endpoint
                    url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={trading_pair}'
                    logger.info(f"Calling Binance API: {url}")
                    response = requests.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Store the data under the base symbol without USDT suffix
                        store_symbol = base_symbol.replace('USDT', '')
                        changes_data[store_symbol] = {
                            'priceChange': float(data['priceChange']),
                            'priceChangePercent': float(data['priceChangePercent']),
                            'lastPrice': float(data['lastPrice']),
                            'volume': float(data['volume']),
                            'quoteVolume': float(data['quoteVolume'])
                        }
                        logger.info(f"Got change data for {store_symbol}: {changes_data[store_symbol]['priceChangePercent']}%")
                except Exception as e:
                    logger.error(f"Error fetching 24hr change for {trading_pair}: {e}")
                    # If we can't get the data, we'll just skip this symbol
            
            return changes_data
        except Exception as e:
            logger.error(f"Error fetching 24hr changes: {e}")
            return {}
    
    def get_historical_klines(self, symbol: str, interval: str = '1d', limit: int = 30):
        """Get historical kline data for a symbol"""
        try:
            # Format the symbol for API call if needed
            trading_pair = symbol
            if not symbol.endswith('USDT'):
                trading_pair = f"{symbol}USDT"
                
            return self.client.get_historical_klines(
                trading_pair,
                interval,
                limit=limit
            )
        except BinanceAPIException as e:
            logger.error(f"Error fetching historical klines for {symbol}: {e}")
            return []

    def format_holdings_response(self, holdings: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Format holdings data into the structure expected by the frontend"""
        try:
            # Initialize response structure
            formatted_data = {
                'spot_holdings': {},
                'margin_holdings': {},
                'futures_holdings': {},
                'total_value': 0,
                'spot_value': 0,
                'margin_value': 0,
                'futures_value': 0,
                'change_24h': 0
            }
            
            # Track total values and changes for weighted average
            total_value = 0
            total_weighted_change = 0
            
            # Process each holding
            for symbol, holding in holdings.items():
                # Extract the type from the symbol (e.g., "BTC_spot" -> "spot")
                holding_type = symbol.split('_')[-1]
                
                # Skip if the holding has no value
                if holding.get('total_usd', 0) == 0 and holding.get('net_asset_usd', 0) == 0:
                    continue
                
                # Calculate holding value based on type
                if holding_type == 'spot':
                    value = holding.get('total_usd', 0)
                    formatted_data['spot_value'] += value
                    formatted_data['spot_holdings'][symbol] = holding
                elif holding_type == 'margin':
                    value = holding.get('net_asset_usd', 0)
                    formatted_data['margin_value'] += value
                    formatted_data['margin_holdings'][symbol] = holding
                elif holding_type == 'futures':
                    value = holding.get('usd_value', 0)
                    formatted_data['futures_value'] += value
                    formatted_data['futures_holdings'][symbol] = holding
                
                # Add to total value
                total_value += value
                
                # Calculate weighted 24h change
                if 'change_24h' in holding and holding['change_24h'] is not None:
                    total_weighted_change += holding['change_24h'] * value
            
            # Set total value
            formatted_data['total_value'] = total_value
            
            # Calculate weighted average 24h change
            if total_value > 0:
                formatted_data['change_24h'] = total_weighted_change / total_value
            
            return {
                'status': 'success',
                'data': formatted_data
            }
            
        except Exception as e:
            logger.error(f"Error formatting holdings response: {e}")
            return {
                'status': 'error',
                'data': {
                    'message': str(e),
                    'spot_holdings': {},
                    'margin_holdings': {},
                    'futures_holdings': {},
                    'total_value': 0,
                    'spot_value': 0,
                    'margin_value': 0,
                    'futures_value': 0,
                    'change_24h': 0
                }
            }

    def get_formatted_holdings(self) -> Dict[str, Any]:
        """Get formatted holdings data from all account types"""
        try:
            # Fetch holdings from all account types
            spot_holdings = self.fetch_spot_holdings()
            margin_holdings = self.fetch_margin_holdings()
            futures_holdings = self.fetch_futures_holdings()
            
            # Get symbols for 24hr changes
            all_symbols = set()
            for symbol in list(spot_holdings.keys()) + list(margin_holdings.keys()) + list(futures_holdings.keys()):
                all_symbols.add(symbol)
            
            # Fetch 24hr changes for all symbols
            changes_data = self.fetch_24hr_changes(list(all_symbols))
            
            # Process and combine all holdings
            holdings = {}
            total_value = 0
            spot_value = 0
            margin_value = 0
            futures_value = 0
            total_weighted_change = 0
            
            # Process spot holdings
            for symbol, data in spot_holdings.items():
                if symbol in changes_data:
                    data['change_24h'] = changes_data[symbol]['priceChangePercent']
                holdings[f"{symbol}_spot"] = data
                value = data.get('total_usd', 0)
                spot_value += value
                total_value += value
                if 'change_24h' in data and data['change_24h'] is not None:
                    total_weighted_change += data['change_24h'] * value
            
            # Process margin holdings
            for symbol, data in margin_holdings.items():
                if symbol in changes_data:
                    data['change_24h'] = changes_data[symbol]['priceChangePercent']
                holdings[f"{symbol}_margin"] = data
                value = data.get('net_asset_usd', 0)
                margin_value += value
                total_value += value
                if 'change_24h' in data and data['change_24h'] is not None:
                    total_weighted_change += data['change_24h'] * value
            
            # Process futures holdings
            for symbol, data in futures_holdings.items():
                if symbol in changes_data:
                    data['change_24h'] = changes_data[symbol]['priceChangePercent']
                holdings[f"{symbol}_futures"] = data
                value = data.get('usd_value', 0)
                futures_value += value
                total_value += value
                if 'change_24h' in data and data['change_24h'] is not None:
                    total_weighted_change += data['change_24h'] * value
            
            # Calculate weighted average 24h change
            change_24h = total_weighted_change / total_value if total_value > 0 else 0
            
            logger.info(f"Successfully processed {len(holdings)} total holdings")
            return {
                'status': 'success',
                'data': {
                    'spot_holdings': {k: v for k, v in holdings.items() if k.endswith('_spot')},
                    'margin_holdings': {k: v for k, v in holdings.items() if k.endswith('_margin')},
                    'futures_holdings': {k: v for k, v in holdings.items() if k.endswith('_futures')},
                    'total_value': total_value,
                    'spot_value': spot_value,
                    'margin_value': margin_value,
                    'futures_value': futures_value,
                    'change_24h': change_24h
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting formatted holdings: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            } 