import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState, useRef } from 'react';
import ChatBox from '../components/ChatBox';
import { Chart, registerables } from 'chart.js';
import KiteHoldingsTable from '../components/KiteHoldingsTable';
import ApiService from '../services/apiService';

// Register Chart.js components
Chart.register(...registerables);

interface LoginFormData {
  user_id: string;
  password: string;
  totp_secret: string;
}

interface KiteHolding {
  trading_symbol: string;
  quantity: number;
  average_price: number;
  last_price: number;
  pnl: number;
  product: string;
  exchange: string;
  instrument_token: number;
  t1_quantity: number;
  realised_quantity: number;
  authorised_quantity: number;
  opening_quantity: number;
  collateral_quantity: number;
  collateral_type: string;
  isin: string;
}

interface ValidationError {
  msg: string;
  type: string;
  loc: string[];
}

function KitePortfolio() {
  const navigate = useNavigate();
  const chartRef = useRef<HTMLCanvasElement | null>(null);
  const [chartInstance, setChartInstance] = useState<Chart | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [portfolioData, setPortfolioData] = useState({
    total_value: 0,
    change_24h: 0,
    holdings_count: 0,
    equity_value: 0,
    mutual_fund_value: 0,
    last_updated: new Date().toLocaleTimeString(),
    total_pnl: 0,
    invested_value: 0
  });
  
  const [equityHoldings, setEquityHoldings] = useState<KiteHolding[]>([]);
  const [mutualFundHoldings, setMutualFundHoldings] = useState<KiteHolding[]>([]);
  const [loginFormData, setLoginFormData] = useState<LoginFormData>({
    user_id: '',
    password: '',
    totp_secret: ''
  });

  // Format currency values
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Format percentage values
  const formatPercentage = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: 'always'
    }).format(value / 100);
  };

  // Check for existing session
  useEffect(() => {
    const accessToken = localStorage.getItem('kite_access_token');
    if (accessToken) {
      console.log('Found access token, fetching portfolio data...');
      setIsAuthenticated(true);
      fetchPortfolioData();
    } else {
      console.log('No access token found');
      setIsLoading(false);
    }
  }, []);

  // Fetch portfolio data
  const fetchPortfolioData = async () => {
    try {
      console.log('Fetching portfolio data...');
      setIsLoading(true);
      setError(null);

      const portfolioResponse = await ApiService.getKitePortfolio();
      console.log('Portfolio response:', portfolioResponse);
      
      if (portfolioResponse.status === 'success' && portfolioResponse.data?.portfolio) {
        const portfolio = portfolioResponse.data.portfolio;
        console.log('Portfolio data:', portfolio);
        
        // Calculate invested value (total value - total P&L)
        const investedValue = portfolio.net_value - portfolio.total_pnl;
        
        // Update portfolio data
        setPortfolioData({
          total_value: portfolio.net_value || 0,
          change_24h: portfolio.total_pnl || 0,
          holdings_count: portfolio.holdings?.length || 0,
          equity_value: portfolio.holdings?.reduce((sum: number, h: KiteHolding) => sum + (h.quantity * h.last_price), 0) || 0,
          mutual_fund_value: 0,
          last_updated: new Date().toLocaleTimeString(),
          total_pnl: portfolio.total_pnl || 0,
          invested_value: investedValue
        });

        // Separate equity and mutual fund holdings
        const equity = portfolio.holdings?.filter((h: KiteHolding) => h.product === 'CNC') || [];
        const mutualFunds = portfolio.holdings?.filter((h: KiteHolding) => h.product === 'MIS') || [];
        
        setEquityHoldings(equity);
        setMutualFundHoldings(mutualFunds);
      } else {
        setError('Failed to fetch portfolio data: ' + (portfolioResponse.data?.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Portfolio fetch error:', error);
      setError('Error fetching portfolio data: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('kite_access_token');
    localStorage.removeItem('kite_public_token');
    setIsAuthenticated(false);
    setPortfolioData({
      total_value: 0,
      change_24h: 0,
      holdings_count: 0,
      equity_value: 0,
      mutual_fund_value: 0,
      last_updated: new Date().toLocaleTimeString(),
      total_pnl: 0,
      invested_value: 0
    });
    setEquityHoldings([]);
    setMutualFundHoldings([]);
  };

  // Handle auto login
  const handleAutoLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await ApiService.kiteAutoLogin(loginFormData);
      console.log('Login response:', response);
      
      if (response.status === 'success' && response.data?.access_token) {
        // Store tokens in localStorage
        localStorage.setItem('kite_access_token', response.data.access_token);
        if (response.data.public_token) {
          localStorage.setItem('kite_public_token', response.data.public_token);
        }
        setIsAuthenticated(true);
        
        // Fetch portfolio data immediately after successful login
        try {
          const portfolioResponse = await ApiService.getKitePortfolio();
          console.log('Portfolio response:', portfolioResponse);
          
          if (portfolioResponse.status === 'success' && portfolioResponse.data?.portfolio) {
            const portfolio = portfolioResponse.data.portfolio;
            console.log('Portfolio data:', portfolio);
            
            // Calculate invested value (total value - total P&L)
            const investedValue = portfolio.net_value - portfolio.total_pnl;
            
            // Update portfolio data
            setPortfolioData({
              total_value: portfolio.net_value || 0,
              change_24h: portfolio.total_pnl || 0,
              holdings_count: portfolio.holdings?.length || 0,
              equity_value: portfolio.holdings?.reduce((sum: number, h: KiteHolding) => sum + (h.quantity * h.last_price), 0) || 0,
              mutual_fund_value: 0,
              last_updated: new Date().toLocaleTimeString(),
              total_pnl: portfolio.total_pnl || 0,
              invested_value: investedValue
            });

            // Separate equity and mutual fund holdings
            const equity = portfolio.holdings?.filter((h: KiteHolding) => h.product === 'CNC') || [];
            const mutualFunds = portfolio.holdings?.filter((h: KiteHolding) => h.product === 'MIS') || [];
            
            setEquityHoldings(equity);
            setMutualFundHoldings(mutualFunds);
          } else {
            setError('Failed to fetch portfolio data: ' + (portfolioResponse.data?.message || 'Unknown error'));
          }
        } catch (portfolioError) {
          console.error('Portfolio fetch error:', portfolioError);
          setError('Error fetching portfolio data: ' + (portfolioError instanceof Error ? portfolioError.message : 'Unknown error'));
        }
      } else {
        // Handle error cases
        const errorMessage = response.data?.message || response.data?.detail || 'Auto login failed';
        console.error('Login failed:', errorMessage);
        setError(errorMessage);
      }
    } catch (error) {
      console.error('Auto login error:', error);
      setError(error instanceof Error ? error.message : 'Auto login failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setLoginFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Initialize chart
  useEffect(() => {
    if (!portfolioData.total_value) return; // Don't create chart if no data

    let chart: Chart | null = null;

    const initChart = () => {
      if (!chartRef.current) return;

      const ctx = chartRef.current.getContext('2d');
      if (!ctx) return;

      chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Equity', 'Mutual Funds'],
          datasets: [{
            data: [
              portfolioData.equity_value, 
              portfolioData.mutual_fund_value
            ],
            backgroundColor: [
              '#3b82f6', // Blue for Equity
              '#f59e0b'  // Orange for Mutual Funds
            ],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '65%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: '#e2e8f0',
                font: {
                  family: "'Inter', sans-serif",
                  size: 12
                },
                boxWidth: 12,
                padding: 10
              }
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.raw as number;
                  const total = portfolioData.total_value;
                  const percentage = ((value / total) * 100).toFixed(2);
                  return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
      
      setChartInstance(chart);
    };

    // Destroy existing chart before creating a new one
    if (chartInstance) {
      chartInstance.destroy();
    }

    setChartInstance(null);

    // Create new chart
    initChart();

    // Cleanup on unmount or before re-render
    return () => {
      if (chart) {
        chart.destroy();
      }
    };
  }, [portfolioData.equity_value, portfolioData.mutual_fund_value, portfolioData.total_value]);

  // Handle chat queries
  const handleChatQuery = async (query: string) => {
    try {
      console.log('Processing chat query:', query);
      const response = await ApiService.processKiteQuery(query);
      console.log('Chat query response:', response);
      
      if (response.status === 'success') {
        return response.data;
      } else {
        throw new Error(response.data?.message || 'Failed to process query');
      }
    } catch (error) {
      console.error('Chat query error:', error);
      return { error: 'Failed to process your query: ' + (error instanceof Error ? error.message : 'Unknown error') };
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900">
        <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/30 rounded-xl p-8 max-w-md w-full">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <img 
                src="https://images.seeklogo.com/logo-png/48/1/zerodha-kite-logo-png_seeklogo-487028.png"
                alt="Kite Logo"
                className="w-12 h-12 object-contain"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.onerror = null;
                  target.src = "https://zerodha.com/static/images/logo.svg";
                }}
              />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Connect to Kite</h1>
            <p className="text-slate-400">Enter your Kite credentials to view your portfolio</p>
          </div>
          
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
              <p className="text-red-500 text-sm">{error}</p>
            </div>
          )}
          
          <form onSubmit={handleAutoLogin} className="space-y-4">
            <div>
              <label htmlFor="user_id" className="block text-sm font-medium text-slate-400 mb-1">
                User ID
              </label>
              <input
                type="text"
                id="user_id"
                name="user_id"
                value={loginFormData.user_id}
                onChange={handleInputChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-400 mb-1">
                Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={loginFormData.password}
                onChange={handleInputChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            
            <div>
              <label htmlFor="totp_secret" className="block text-sm font-medium text-slate-400 mb-1">
                TOTP Secret
              </label>
              <input
                type="password"
                id="totp_secret"
                name="totp_secret"
                value={loginFormData.totp_secret}
                onChange={handleInputChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            
            <button
              type="submit"
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-4 rounded-lg transition-colors"
            >
              Login
            </button>
          </form>
          
          <p className="text-slate-500 text-sm text-center mt-4">
            Enter your Kite credentials to access your portfolio
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-slate-800/50 rounded-full flex items-center justify-center mr-3 shadow-lg border border-slate-700/30">
              <img 
                src="https://images.seeklogo.com/logo-png/48/1/zerodha-kite-logo-png_seeklogo-487028.png"
                alt="Kite Logo"
                className="w-8 h-8 object-contain"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.onerror = null;
                  target.src = "https://zerodha.com/static/images/logo.svg";
                }}
              />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-blue-600">
                Kite Portfolio
              </h1>
              <p className="text-slate-400 text-sm mt-1 flex items-center">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                Real-time stock market portfolio analysis and insights
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-white transition-colors"
            >
              Logout
            </button>
            <Link to="/portfolio" className="text-blue-400 hover:text-blue-300 transition-colors p-2 bg-slate-800/50 rounded-full">
              <ArrowLeft className="h-6 w-6" />
            </Link>
          </div>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main Content - 2/3 width */}
        <div className="lg:w-2/3">
          {/* Portfolio Overview */}
          <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/30 rounded-xl p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 border-l-4 border-blue-500 pl-3">Portfolio Overview</h2>
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="lg:w-3/5">
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="bg-slate-800 rounded-lg p-3">
                    <p className="text-slate-400 text-xs">Total Value</p>
                    <p className="text-xl font-bold">{formatCurrency(portfolioData.total_value)}</p>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-3">
                    <p className="text-slate-400 text-xs">Total P&L</p>
                    <div className="flex items-baseline gap-1">
                      <p className={`text-xl font-bold ${portfolioData.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {formatCurrency(portfolioData.total_pnl)}
                      </p>
                      <p className={`text-sm ${portfolioData.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        ({formatPercentage((portfolioData.total_pnl / portfolioData.invested_value) * 100)})
                      </p>
                    </div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-3">
                    <p className="text-slate-400 text-xs">Holdings</p>
                    <p className="text-xl font-bold">{portfolioData.holdings_count}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-xs">Equity Value</span>
                      <span className="font-medium text-slate-200 text-sm">{formatCurrency(portfolioData.equity_value)}</span>
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-xs">Mutual Fund Value</span>
                      <span className="font-medium text-slate-200 text-sm">{formatCurrency(portfolioData.mutual_fund_value)}</span>
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-xs">Last Updated</span>
                      <span className="font-medium text-slate-200 text-sm">{portfolioData.last_updated}</span>
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-xs">Invested Value</span>
                      <span className="font-medium text-slate-200 text-sm">{formatCurrency(portfolioData.invested_value)}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="lg:w-2/5">
                <div className="h-40">
                  <canvas ref={chartRef}></canvas>
                </div>
              </div>
            </div>
          </div>

          {/* Holdings */}
          <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/30 rounded-xl p-6">
            <h2 className="text-xl font-semibold mb-4 border-l-4 border-blue-500 pl-3">Holdings</h2>
            
            {/* Equity Section */}
            <div className="mb-8">
              <h3 className="text-lg font-medium mb-3 text-blue-400">Equity Holdings</h3>
              <KiteHoldingsTable holdings={equityHoldings} />
            </div>
            
            {/* Mutual Funds Section */}
            <div>
              <h3 className="text-lg font-medium mb-3 text-blue-400">Mutual Funds</h3>
              <KiteHoldingsTable holdings={mutualFundHoldings} />
            </div>
          </div>
        </div>

        {/* Chat Box - 1/3 width */}
        <div className="lg:w-1/3">
          <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/30 rounded-xl p-6 sticky top-4">
            <h2 className="text-xl font-semibold mb-4 border-l-4 border-blue-500 pl-3">Portfolio Query</h2>
            <p className="text-slate-400 text-sm mb-4">
              Ask questions about your portfolio and get instant insights.
            </p>
            <ChatBox 
              initialMessage="Hello! I can help you analyze your Kite portfolio. What would you like to know?"
              placeholder="Ask about your portfolio..."
              onSendMessage={handleChatQuery}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default KitePortfolio;