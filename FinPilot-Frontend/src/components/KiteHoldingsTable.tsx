import React from 'react';

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

interface KiteHoldingsTableProps {
  holdings: KiteHolding[];
}

function KiteHoldingsTable({ holdings }: KiteHoldingsTableProps) {
  // Format currency values
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Format number with appropriate decimals
  const formatNumber = (value: number, decimals = 2) => {
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: value < 0.1 ? decimals : 2,
      maximumFractionDigits: value < 0.1 ? decimals : 2
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

  // Calculate P&L percentage
  const calculatePnLPercentage = (holding: KiteHolding) => {
    const investment = holding.quantity * holding.average_price;
    if (investment === 0) return 0;
    return (holding.pnl / investment) * 100;
  };

  return (
    <div className="overflow-x-auto">
      {holdings.length > 0 ? (
        <table className="w-full border-separate border-spacing-0">
          <thead>
            <tr className="text-left">
              <th className="pb-3 pr-4 text-slate-300 font-medium text-base sticky left-0 bg-slate-900/30">
                <div className="border-b-2 border-blue-500 pb-1 inline-block">Symbol</div>
              </th>
              <th className="pb-3 pr-4 text-slate-300 font-medium text-base">
                <div className="border-b-2 border-green-500 pb-1 inline-block">
                  <div>Quantity</div>
                  <div className="text-xs text-slate-400 mt-0.5">Value</div>
                </div>
              </th>
              <th className="pb-3 pr-4 text-slate-300 font-medium text-base">
                <div className="border-b-2 border-purple-500 pb-1 inline-block">
                  <div>Price</div>
                  <div className="text-xs text-slate-400 mt-0.5">Avg Price</div>
                </div>
              </th>
              <th className="pb-3 pr-4 text-slate-300 font-medium text-base">
                <div className="border-b-2 border-orange-500 pb-1 inline-block">
                  <div>P&L</div>
                  <div className="text-xs text-slate-400 mt-0.5">%</div>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((holding, index) => (
              <tr key={index} className={`group relative transition-all duration-200 hover:bg-slate-800/50 ${index !== 0 ? "border-t border-slate-700/20" : ""}`}>
                <td className="py-3 pr-4 sticky left-0 bg-slate-900/30 group-hover:bg-slate-800/50">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500/80 to-blue-600/50 flex items-center justify-center text-sm font-bold">
                      {holding.trading_symbol.substring(0, 2)}
                    </div>
                    <div className="text-lg font-bold text-white tracking-wide">
                      {holding.trading_symbol}
                    </div>
                  </div>
                </td>
                
                <td className="py-3 pr-4">
                  <div className="text-base font-medium text-slate-200">
                    {formatNumber(holding.quantity)} <span className="text-sm text-slate-400">shares</span>
                  </div>
                  <div className="text-sm text-slate-400 mt-0.5">
                    {formatCurrency(holding.quantity * holding.last_price)}
                  </div>
                </td>
                
                <td className="py-3 pr-4">
                  <div className="text-base font-medium text-slate-200">
                    {formatCurrency(holding.last_price)}
                  </div>
                  <div className="text-sm text-slate-400 mt-0.5">
                    {formatCurrency(holding.average_price)}
                  </div>
                </td>
                
                <td className="py-3 pr-4">
                  <div className={`text-base font-medium ${
                    holding.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {formatCurrency(holding.pnl)}
                  </div>
                  <div className={`text-sm mt-0.5 ${
                    holding.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {formatPercentage(calculatePnLPercentage(holding))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="bg-slate-800/50 rounded-lg p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-700/50 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <p className="text-slate-400">No holdings found in this category.</p>
          <p className="text-slate-500 text-sm mt-1">Holdings will appear here once you have assets in this section.</p>
        </div>
      )}
    </div>
  );
}

export default KiteHoldingsTable; 