import asyncio
import sys
import os
import traceback
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python_backend.binance.portfolio_manager import BinancePortfolioManager

async def test_portfolio_query():
    """Test the portfolio query functionality"""
    try:
        print("Initializing BinancePortfolioManager...")
        manager = BinancePortfolioManager()
        
        # Sample queries to test
        test_queries = [
            "What's the total value of my portfolio?",
            "How much have I invested in Bitcoin?",
            "What's my portfolio performance in the last month?"
        ]
        
        for query in test_queries:
            print(f"\n\n[TEST QUERY] {query}")
            
            try:
                # Process the query
                result = await manager.process_query(query)
                
                # Print the result
                print(f"[STATUS] {result['status']}")
                if 'message' in result:
                    print(f"[MESSAGE] {result['message']}")
                if 'response' in result:
                    print(f"[RESPONSE] {result['response']}")
                
            except Exception as e:
                print(f"[ERROR] {str(e)}")
                print(f"[TRACEBACK] {traceback.format_exc()}")
        
        print("\n\nTest completed successfully!")
    except Exception as e:
        print(f"[FATAL ERROR] {str(e)}")
        print(f"[TRACEBACK] {traceback.format_exc()}")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_portfolio_query()) 