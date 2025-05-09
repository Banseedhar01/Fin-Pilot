from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path
from typing import Dict, Any, Union, Optional
from pydantic import BaseModel
from python_backend.binance.portfolio_manager import BinancePortfolioManager
from python_backend.core.config import get_settings
from datetime import datetime

# Get settings
settings = get_settings()

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


# Initialize portfolio manager
binance_portfolio_manager = BinancePortfolioManager()

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
@app.get("/api/kite/portfolio/holdings", response_model=Response, tags=["Kite Portfolio"])
async def get_kite_holdings():
    """
    Get Kite portfolio holdings
    
    Returns a list of all holdings in your Kite portfolio with details
    """
    try:
        holdings = kite_portfolio_agent.get_holdings()
        return holdings
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
        response = kite_portfolio_agent.process_query(query.text)
        return response
    except Exception as e:
        return create_response("error", message=str(e))

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