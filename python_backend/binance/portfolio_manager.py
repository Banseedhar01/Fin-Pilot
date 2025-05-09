from typing import Dict, Any
import asyncio
from .portfolio_data.client import BinancePortfolioClient
from .vectordb_storage.storage import VectorDBStorage
from ..core.logger import setup_logger
from .agents.query_agent import BinanceLangGraphAgent

logger = setup_logger(__name__)

class BinancePortfolioManager:
    """Manages portfolio operations and coordinates between client and storage"""
    
    def __init__(self):
        """Initialize portfolio manager with client and storage"""
        self.client = BinancePortfolioClient()
        self.storage = VectorDBStorage()
        self._query_agent = None  # Lazy initialization of query agent
        logger.info("Portfolio manager initialized")
    
    async def _update_vector_db(self, holdings_data: Dict[str, Any]):
        """Update vector DB asynchronously"""
        try:
            await self.storage.store_portfolio_data(holdings_data)
            logger.info("Successfully stored holdings in vector DB")
        except Exception as e:
            logger.error(f"Error storing holdings in vector DB: {str(e)}")
    
    def get_holdings(self) -> Dict[str, Any]:
        """Get current portfolio holdings with market data"""
        try:
            # Get holdings data from client
            holdings_data = self.client.get_formatted_holdings()
            
            if holdings_data['status'] == 'success':
                # Start vector DB update in background without waiting
                asyncio.create_task(self._update_vector_db(holdings_data['data']))
                logger.info("Started async vector DB update")
            
            # Return holdings data immediately
            return holdings_data
            
        except Exception as e:
            logger.error(f"Error getting holdings: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @property
    def query_agent(self):
        """Lazy initialization of query agent"""
        if self._query_agent is None:
            logger.info("Initializing query agent with existing vector storage")
            # Pass the existing vector storage to avoid duplication
            self._query_agent = BinanceLangGraphAgent(vector_storage=self.storage)
        return self._query_agent
    
    async def process_query(self, query_text: str) -> Dict[str, Any]:
        """
        Process a user query about the portfolio
        
        Args:
            query_text: The text of the user's query
            
        Returns:
            Dict containing the response and status
        """
        try:
            logger.info(f"Processing portfolio query: '{query_text}'")
            
            # Ensure holdings are up-to-date in vector DB
            holdings = self.get_holdings()
            if holdings['status'] == 'success':
                logger.info("Updated holdings before processing query")
            
            # Process query using the query agent
            result = self.query_agent.process_query(query_text)
            
            logger.info("Query processed successfully")
            return result
        except Exception as e:
            logger.error(f"Error processing portfolio query: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'response': "I encountered an error while processing your query. Please try again."
            } 