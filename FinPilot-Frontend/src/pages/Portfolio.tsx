import { Link } from 'react-router-dom';
import { ArrowLeft, TrendingUp, Wallet, Activity, ArrowUpRight, ArrowDownRight, Coins, LineChart } from 'lucide-react';
import { useEffect, useState } from 'react';
import ApiService from '../services/apiService';

function Portfolio() {
  const [binanceData, setBinanceData] = useState({
    total_value: 0,
    change_24h: 0,
    total_invested: 0,
    total_pnl: 0,
    spot_value: 0,
    margin_value: 0,
    futures_value: 0,
    last_updated: new Date().toLocaleTimeString()
  });
  const [kiteData, setKiteData] = useState({
    total_value: 0,
    change_24h: 0,
    total_invested: 0,
    total_pnl: 0,
    equity_value: 0,
    margin_value: 0
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Cache management
  const loadCachedData = () => {
    try {
      const cachedDataStr = localStorage.getItem('binance_portfolio_data');
      if (cachedDataStr) {
        const cachedData = JSON.parse(cachedDataStr);
        if (cachedData && typeof cachedData === 'object' && 
            'total_value' in cachedData && 
            'change_24h' in cachedData) {
          cachedData.last_updated = `${new Date(cachedData.last_updated).toLocaleTimeString()} (cached)`;
          setBinanceData(cachedData);
          return true;
        }
      }
      return false;
    } catch (error) {
      console.error('Error loading cached data:', error);
      return false;
    }
  };

  // Fetch Binance portfolio data
  const fetchBinanceData = async (isBackgroundRefresh = false) => {
    if (isBackgroundRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const response = await ApiService.getBinanceHoldings();
      
      if (response.status === 'success' && response.data) {
        const data = response.data;
        
        const updatedData = {
          total_value: data.total_value || 0,
          change_24h: data.change_24h || 0,
          total_invested: data.total_invested || 0,
          total_pnl: data.total_pnl || 0,
          spot_value: data.spot_value || 0,
          margin_value: data.margin_value || 0,
          futures_value: data.futures_value || 0,
          last_updated: new Date().toLocaleTimeString()
        };

        setBinanceData(updatedData);
        localStorage.setItem('binance_portfolio_data', JSON.stringify(updatedData));
      } else {
        throw new Error(response.data?.message || 'Failed to fetch Binance data');
      }
    } catch (error) {
      console.error('Error fetching Binance data:', error);
      if (!isBackgroundRefresh) {
        setError(error instanceof Error ? error.message : 'Failed to load Binance portfolio');
      }
    } finally {
      if (isBackgroundRefresh) {
        setIsRefreshing(false);
      } else {
        setIsLoading(false);
      }
    }
  };

  // Fetch data on initial load and set up refresh interval
  useEffect(() => {
    // First try to load cached data for immediate display
    const hasCachedData = loadCachedData();
    
    // Then fetch fresh data
    if (hasCachedData) {
      fetchBinanceData(true);
    } else {
      fetchBinanceData(false);
    }
    
    // Set up refresh interval - every 30 seconds
    const intervalId = setInterval(() => fetchBinanceData(true), 30000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  // Format currency values
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Format percentage values
  const formatPercentage = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value / 100);
  };

  // Add these calculation functions after the formatPercentage function
  const calculateTotalPnL = (holdings: any[]): number => {
    return holdings.reduce((total, holding) => {
      if (holding.pnl !== undefined && isFinite(holding.pnl)) {
        return total + holding.pnl;
      }
      return total;
    }, 0);
  };

  const calculateTotalPnLPercentage = (holdings: any[]): string => {
    const totalInvestment = holdings.reduce((total, holding) => {
      return total + (holding.total_usd || 0);
    }, 0);
    
    const totalPnL = calculateTotalPnL(holdings);
    
    if (totalInvestment > 0) {
      const percentage = (totalPnL / totalInvestment) * 100;
      return percentage.toFixed(2);
    }
    
    return '0.00';
  };

  // Calculate total portfolio value
  const totalPortfolioValue = binanceData.total_value + kiteData.total_value;
  const totalPortfolioPercentage = ((binanceData.change_24h * binanceData.total_value + kiteData.change_24h * kiteData.total_value) / totalPortfolioValue);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800">
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Link to="/" className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors">
              <ArrowLeft className="h-5 w-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white">Portfolio</h1>
              <p className="text-sm text-slate-400">Track your investments</p>
            </div>
          </div>
          {(isLoading || isRefreshing) && (
            <div className="flex items-center text-sm text-slate-400">
              <span className="inline-flex items-center mr-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse mr-1"></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse opacity-75 mr-1" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse opacity-50" style={{ animationDelay: '0.4s' }}></div>
              </span>
              Updating...
            </div>
          )}
        </div>

        {/* Main Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Wallet className="h-5 w-5 text-blue-400" />
              </div>
              <span className="text-sm text-slate-400">Total Value</span>
            </div>
            <p className="text-2xl font-bold text-white">{formatCurrency(totalPortfolioValue)}</p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <TrendingUp className="h-5 w-5 text-green-400" />
              </div>
              <span className="text-sm text-slate-400">24h Change</span>
            </div>
            <p className={`text-2xl font-bold ${totalPortfolioPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatPercentage(totalPortfolioPercentage)}
            </p>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <Activity className="h-5 w-5 text-purple-400" />
              </div>
              <span className="text-sm text-slate-400">Active Investments</span>
            </div>
            <p className="text-2xl font-bold text-white">2</p>
          </div>
        </div>

        {/* Portfolio Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Binance Card */}
          <Link
            to="/binance-portfolio"
            className="group bg-slate-800/50 backdrop-blur-sm border border-slate-700/30 rounded-xl p-4 hover:bg-slate-800/70 transition-all duration-300"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/10 rounded-lg flex items-center justify-center">
                  <img 
                    src="https://bin.bnbstatic.com/static/images/common/favicon.ico"
                    alt="Binance Logo"
                    className="w-6 h-6 object-contain"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.onerror = null;
                      target.src = "https://bin.bnbstatic.com/static/images/common/logo.png";
                    }}
                  />
                </div>
                <h2 className="text-lg font-semibold text-white">Binance</h2>
              </div>
              <span className="text-sm text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">View →</span>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              {/* Left Column */}
              <div className="space-y-3">
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">Current Value</p>
                  <p className="text-lg font-semibold text-white">{formatCurrency(binanceData.total_value)}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">Total Returns</p>
                  <div>
                    <p className={`text-lg font-semibold ${binanceData.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(binanceData.total_pnl)}
                    </p>
                    <p className={`text-sm ${binanceData.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {binanceData.total_invested > 0 ? 
                        `(${formatPercentage((binanceData.total_pnl / binanceData.total_invested) * 100)})` : 
                        '(0.00%)'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Right Column */}
              <div className="space-y-3">
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">Invested</p>
                  <p className="text-lg font-semibold text-white">{formatCurrency(binanceData.total_invested)}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">24H P&L</p>
                  <div>
                    <p className={`text-lg font-semibold ${binanceData.change_24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(binanceData.total_value * (binanceData.change_24h / 100))}
                    </p>
                    <p className={`text-sm ${binanceData.change_24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ({formatPercentage(binanceData.change_24h)})
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-3 bg-slate-800/50 rounded-lg p-3">
              <p className="text-xs text-slate-400">Allocation</p>
              <p className="text-lg font-semibold text-white">
                {formatPercentage((binanceData.total_value / totalPortfolioValue) * 100)} of Portfolio
              </p>
            </div>
          </Link>

          {/* Kite Card */}
          <Link
            to="/kite-portfolio"
            className="group bg-slate-800/50 backdrop-blur-sm border border-slate-700/30 rounded-xl p-4 hover:bg-slate-800/70 transition-all duration-300"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg flex items-center justify-center">
                  <img 
                    src="https://images.seeklogo.com/logo-png/48/1/zerodha-kite-logo-png_seeklogo-487028.png"
                    alt="Kite Logo"
                    className="w-6 h-6 object-contain"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.onerror = null;
                      target.src = "https://zerodha.com/static/images/logo.svg";
                    }}
                  />
                </div>
                <h2 className="text-lg font-semibold text-white">Kite</h2>
              </div>
              <span className="text-sm text-green-400 opacity-0 group-hover:opacity-100 transition-opacity">View →</span>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              {/* Left Column */}
              <div className="space-y-3">
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">Current Value</p>
                  <p className="text-lg font-semibold text-white">{formatCurrency(kiteData.total_value)}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">Total Returns</p>
                  <div>
                    <p className={`text-lg font-semibold ${kiteData.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(kiteData.total_pnl)}
                    </p>
                    <p className={`text-sm ${kiteData.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ({formatPercentage((kiteData.total_pnl / kiteData.total_invested) * 100)})
                    </p>
                  </div>
                </div>
              </div>

              {/* Right Column */}
              <div className="space-y-3">
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">Invested</p>
                  <p className="text-lg font-semibold text-white">{formatCurrency(kiteData.total_invested)}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400">24H P&L</p>
                  <div>
                    <p className={`text-lg font-semibold ${kiteData.change_24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(kiteData.total_value * (kiteData.change_24h / 100))}
                    </p>
                    <p className={`text-sm ${kiteData.change_24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ({formatPercentage(kiteData.change_24h)})
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-3 bg-slate-800/50 rounded-lg p-3">
              <p className="text-xs text-slate-400">Allocation</p>
              <p className="text-lg font-semibold text-white">
                {formatPercentage((kiteData.total_value / totalPortfolioValue) * 100)} of Portfolio
              </p>
            </div>
          </Link>
        </div>

        {/* Error State */}
        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default Portfolio;