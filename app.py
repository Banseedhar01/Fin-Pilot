from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
from pydantic import BaseModel
from python_backend.binance.portfolio_manager import BinancePortfolioManager
from python_backend.kite.portfolio_manager import KitePortfolioManager
from python_backend.core.config import get_settings
from python_backend.core.logger import setup_logger
from datetime import datetime
import logging

# Get settings
settings = get_settings()

# Setup logger
logger = setup_logger(__name__)

# Define request and response models
class QueryRequest(BaseModel):
    text: str
    
    class Config:
        schema_extra = {
            "example": {
                "text": "What is the current trend for AAPL stock?"
            }
        }

class Response(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "message": "Response message or data"
                }
            }
        }

class PortfolioResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "message": "Response message or data"
                }
            }
        }

class HoldingResponse(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    total_value: float
    pnl: float
    pnl_percentage: float

class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    total_value: float
    pnl: float
    pnl_percentage: float

# Initialize FastAPI app with metadata
app = FastAPI(
    title="FinPilot Financial Advisor",
    description="Your intelligent financial companion for portfolio analysis, market insights, and investment guidance",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware with specific origin for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "*"],  # Allow your React app and others during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize portfolio managers
binance_portfolio_manager = BinancePortfolioManager()
kite_portfolio_manager = KitePortfolioManager()

# Try to mount the React build folder if it exists
react_build_dir = Path("FinPilot-Frontend/build")
if react_build_dir.exists() and react_build_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(react_build_dir), html=True), name="react_app")

# Helper functions
def create_response(status: str, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None) -> Response:
    """Helper function to create standardized API responses"""
    return Response(status=status, data=data, message=message)

##############################
# ---- API ROUTES ---- #
##############################

# ---- General Finance API Routes ----
@app.post("/api/query", response_model=Response, tags=["Finance Queries"])
async def process_query(query: QueryRequest):
    """
    Process a general financial query
    
    - **text**: The query text to process
    
    Returns a response with insights and data related to the query
    """
    global query_agent
    try:
        # Check if query_agent is initialized
        if not query_agent:
            # Reinitialize the query agent
            query_agent = QueryAgent()
        
        response = query_agent._run(query.text)
        return response
    except Exception as e:
        print(f"Error in process_query: {str(e)}")
        return create_response("error", message=str(e))

# ---- Binance Portfolio API Routes ----
@app.post("/api/binance/portfolio/query", response_model=Response, tags=["Binance Portfolio"])
async def process_binance_portfolio_query(query: QueryRequest):
    """
    Process a Binance portfolio-specific query
    
    - **text**: The query text about your Binance portfolio data
    
    Returns insights and analysis about your Binance portfolio based on the query
    """
    try:
        # Process the query using the portfolio manager
        result = await binance_portfolio_manager.process_query(query.text)
        
        if result["status"] == "error":
            return create_response("error", message=result["message"])
        
        return create_response("success", data={"response": result["response"]})
    except Exception as e:
        return create_response("error", message=str(e))

@app.get("/api/binance/portfolio/holdings", response_model=Response, tags=["Binance Portfolio"])
async def get_binance_holdings():
    """
    Get all Binance portfolio holdings
    
    Returns a list of all holdings in your Binance portfolio with details
    """
    try:
        response = binance_portfolio_manager.get_holdings()
        return response
    except Exception as e:
        return create_response("error", message=str(e))

@app.get("/api/binance/portfolio/analysis", response_model=Response, tags=["Binance Portfolio"])
async def analyze_binance_portfolio():
    """
    Perform comprehensive analysis on the Binance portfolio
    
    Returns in-depth analysis of your Binance portfolio including risk metrics and recommendations
    """
    try:
        response = binance_portfolio_agent.analyze_portfolio()
        return response
    except Exception as e:
        return create_response("error", message=str(e))

# ---- Kite Portfolio API Routes ----
@app.get("/api/kite/portfolio", response_model=Response, tags=["Kite Portfolio"])
async def get_kite_portfolio():
    """
    Get complete Kite portfolio data
    
    Returns:
        Response: Complete portfolio data including holdings, positions, net value and total P&L
    """
    try:
        if not kite_portfolio_manager.is_authenticated():
            return create_response("error", message="User not authenticated. Please login first.")
            
        portfolio = kite_portfolio_manager.fetch_portfolio()
        
        # Convert portfolio to dictionary format with consistent data types
        portfolio_dict = {
            "holdings": [
                {
                    "trading_symbol": str(h.trading_symbol or ""),
                    "quantity": int(h.quantity or 0),
                    "average_price": float(h.average_price or 0.0),
                    "last_price": float(h.last_price or 0.0),
                    "pnl": float(h.pnl or 0.0),
                    "product": str(h.product or ""),
                    "exchange": str(h.exchange or ""),
                    "instrument_token": int(h.instrument_token or 0),
                    "t1_quantity": int(h.t1_quantity or 0),
                    "realised_quantity": int(h.realised_quantity or 0),
                    "authorised_quantity": int(h.authorised_quantity or 0),
                    "opening_quantity": int(h.opening_quantity or 0),
                    "collateral_quantity": int(h.collateral_quantity or 0),
                    "collateral_type": str(h.collateral_type or ""),
                    "isin": str(h.isin or "")
                } for h in portfolio.holdings
            ],
            "positions": [
                {
                    "trading_symbol": str(p.trading_symbol or ""),
                    "quantity": int(p.quantity or 0),
                    "average_price": float(p.average_price or 0.0),
                    "last_price": float(p.last_price or 0.0),
                    "pnl": float(p.pnl or 0.0),
                    "product": str(p.product or ""),
                    "exchange": str(p.exchange or ""),
                    "instrument_token": int(p.instrument_token or 0)
                } for p in portfolio.positions
            ],
            "net_value": float(portfolio.net_value or 0.0),
            "total_pnl": float(portfolio.total_pnl or 0.0),
            "last_updated": portfolio.last_updated.isoformat()
        }
        
        return create_response("success", data={"portfolio": portfolio_dict})
    except Exception as e:
        logger.error(f"Error fetching portfolio: {str(e)}")
        return create_response("error", message=str(e))

@app.get("/api/kite/portfolio/holdings", response_model=Response, tags=["Kite Portfolio"])
async def get_kite_holdings():
    """
    Get Kite portfolio holdings
    
    Returns:
        Response: List of all holdings in your Kite portfolio with details
    """
    try:
        if not kite_portfolio_manager.is_authenticated():
            return create_response("error", message="User not authenticated. Please login first.")
            
        holdings = kite_portfolio_manager.get_holdings()
        return create_response("success", data={"holdings": holdings})
    except Exception as e:
        return create_response("error", message=str(e))

@app.get("/api/kite/portfolio/positions", response_model=Response, tags=["Kite Portfolio"])
async def get_kite_positions():
    """
    Get Kite portfolio positions
    
    Returns:
        Response: List of all positions in your Kite portfolio with details
    """
    try:
        if not kite_portfolio_manager.is_authenticated():
            return create_response("error", message="User not authenticated. Please login first.")
            
        positions = kite_portfolio_manager.get_positions()
        return create_response("success", data={"positions": positions})
    except Exception as e:
        return create_response("error", message=str(e))

@app.post("/api/kite/portfolio/query", response_model=Response, tags=["Kite Portfolio"])
async def process_kite_query(query: QueryRequest):
    """
    Process Kite portfolio queries
    
    - **text**: The query text related to your Kite portfolio
    
    Returns analysis and insights about your Kite portfolio based on the query
    """
    try:
        if not kite_portfolio_manager.is_authenticated():
            return create_response("error", message="User not authenticated. Please login first.")
            
        portfolio = kite_portfolio_manager.fetch_portfolio()
        return create_response("success", data={"portfolio": portfolio})
    except Exception as e:
        return create_response("error", message=str(e))

@app.post("/api/kite/auto-login", response_model=Response, tags=["Kite Portfolio"])
async def kite_auto_login(request: Request):
    """
    Auto login to Kite using user credentials and TOTP
    
    Args:
        request: The request object containing user_id, password and totp_secret
        
    Returns:
        Response: Access token and public token
    """
    data = await request.json()
    user_id = data.get('user_id')
    password = data.get('password')
    totp_secret = data.get('totp_secret')
    
    response = kite_portfolio_manager.handle_auto_login(
        user_id=user_id,
        password=password,
        totp_secret=totp_secret
    )
    return create_response(
        status=response["status"],
        data=response.get("data"),
        message=response.get("message")
    )

# ---- System API Routes ----
@app.get("/api/health", tags=["System"])
async def health_check():
    """
    Health check endpoint
    
    Returns the status of the application and its components
    """
    try:
        # Check if portfolio manager is initialized
        portfolio_status = {
            "portfolio_manager": binance_portfolio_manager is not None
        }
        
        return create_response("success", {
            "status": "healthy",
            "components": portfolio_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return create_response("error", message=str(e))

@app.get("/api/version", tags=["System"])
async def version_info():
    """
    Get application version and environment info
    
    Returns version information about the application
    """
    return create_response("success", {
        "app_name": "FinPilot Financial Advisor",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    })

# Route to handle React routing - this allows React Router to handle routes
@app.get("/{full_path:path}", response_class=FileResponse, include_in_schema=False)
async def serve_react_app(full_path: str):
    """
    Catch-all route to support React Router
    
    Returns the React index.html for all non-api routes
    """
    # Check if the request is for an API route
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    
    # Check if React build folder exists
    react_index = Path("FinPilot-Frontend/build/index.html")
    if react_index.exists():
        return FileResponse(str(react_index))
    
    raise HTTPException(status_code=404, detail="Page not found")

if __name__ == "__main__":
    import uvicorn
    print("\n==================================")
    print("FinPilot Financial Advisor starting up!")
    print("Access your application at:")
    print(" • http://localhost:8000")
    print(" • http://127.0.0.1:8000")
    print(" • API Documentation: http://localhost:8000/api/docs")
    print("==================================\n")
    uvicorn.run(app, host="0.0.0.0", port=8000) 