from typing import Dict, Any, List
import json
from datetime import datetime
import logging
from pinecone import Pinecone, ServerlessSpec
from ...core.logger import setup_logger
from ...core.config import get_settings
import asyncio
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Initialize settings and logger
settings = get_settings()
logger = setup_logger(__name__)

# Maximum number of portfolio records to keep
MAX_PORTFOLIO_RECORDS = 5

class VectorDBStorage:
    """Handles storage of portfolio data in Pinecone vector database"""
    
    def __init__(self):
        """Initialize Pinecone vector DB storage"""
        try:
            logger.info("Initializing VectorDBStorage...")
            
            # Initialize OpenAI embeddings
            logger.debug("Initializing OpenAI embeddings...")
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model="text-embedding-ada-002"
            )
            
            # Initialize Pinecone client
            logger.debug("Initializing Pinecone client...")
            self.pc = Pinecone(
                api_key=settings.PINECONE_API_KEY
            )
            
            # Define index name and configuration
            self.index_name = "fin-pilot-portfolio"
            self.dimension = 1536  # Dimension for text-embedding-ada-002
            
            # Create index if it doesn't exist
            logger.debug(f"Checking if index '{self.index_name}' exists...")
            if self.index_name not in self.pc.list_indexes().names():
                logger.info(f"Creating new index '{self.index_name}'...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud='aws',
                        region=settings.PINECONE_ENVIRONMENT
                    )
                )
                logger.info(f"Successfully created index '{self.index_name}'")
            
            # Get the index instance
            self.index = self.pc.Index(self.index_name)
            
            # Initialize specialized LangChain-Pinecone integration
            logger.debug("Initializing LangChain-Pinecone integration...")
            self.vectorstore = PineconeVectorStore(
                embedding=self.embeddings,
                index_name=self.index_name,
                pinecone_api_key=settings.PINECONE_API_KEY,
                text_key="text"
            )
            
            # Initialize text splitter
            logger.debug("Initializing text splitter...")
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            logger.info("VectorDBStorage initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize VectorDBStorage: {str(e)}", exc_info=True)
            raise
    
    async def store_portfolio_data(self, data: Dict[str, Any]) -> str:
        """
        Store portfolio data in Pinecone vector DB asynchronously
        
        Args:
            data: Portfolio data to store
            
        Returns:
            str: ID of the stored portfolio data
            
        Raises:
            Exception: If storage operation fails
        """
        try:
            logger.info("Starting portfolio data storage...")
            
            # Run the storage operation in a thread pool
            vector_id = await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_data,
                data
            )
            
            # Prune old records if needed
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._prune_old_records
            )
            
            logger.info(f"Successfully stored portfolio data with ID: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to store portfolio data: {str(e)}", exc_info=True)
            raise
    
    def _store_data(self, data: Dict[str, Any]) -> str:
        """
        Actual storage implementation in Pinecone
        
        Args:
            data: Portfolio data to store
            
        Returns:
            str: ID of the stored portfolio data
            
        Raises:
            Exception: If storage operation fails
        """
        try:
            # Generate timestamp and ID
            timestamp = datetime.now().isoformat()
            vector_id = f"portfolio_{timestamp.replace(':', '-')}"
            
            logger.debug(f"Processing portfolio data for ID: {vector_id}")
            
            # Store the complete portfolio data as a single document
            # This ensures we have at least one complete copy of the data
            portfolio_text = json.dumps(data, indent=2)
            complete_doc = Document(
                page_content=portfolio_text,
                metadata={
                    'timestamp': timestamp,
                    'portfolio_id': vector_id,
                    'type': 'portfolio_data',
                    'chunk_id': f"{vector_id}_complete",
                    'is_complete': True
                }
            )
            
            # Store the complete document
            logger.debug("Storing complete portfolio document...")
            self.vectorstore.add_documents([complete_doc])
            
            # Also store individual chunks for better semantic search
            # Split into chunks
            logger.debug("Splitting document into chunks for better semantic search...")
            chunks = self.text_splitter.split_documents([
                Document(
                    page_content=portfolio_text,
                    metadata={
                        'timestamp': timestamp,
                        'portfolio_id': vector_id,
                        'type': 'portfolio_data'
                    }
                )
            ])
            
            # Add chunk metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_id'] = f"{vector_id}_chunk_{i}"
                chunk.metadata['is_chunk'] = True
            
            # Store chunks
            if chunks:
                logger.debug(f"Storing {len(chunks)} additional chunks in Pinecone...")
                self.vectorstore.add_documents(chunks)
            
            total_docs = 1 + len(chunks)
            logger.info(f"Successfully stored {total_docs} documents for portfolio ID: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to store data in Pinecone: {str(e)}", exc_info=True)
            raise
    
    def _prune_old_records(self) -> None:
        """
        Maintain only MAX_PORTFOLIO_RECORDS most recent portfolio records in the database
        
        Deletes older records if the number of records exceeds MAX_PORTFOLIO_RECORDS
        """
        try:
            logger.info(f"Checking if pruning is needed (max records: {MAX_PORTFOLIO_RECORDS})...")
            
            # Get all portfolio records, sorted by timestamp
            portfolio_ids = self._get_all_portfolio_ids()
            
            # Check if we need to prune
            if len(portfolio_ids) <= MAX_PORTFOLIO_RECORDS:
                logger.debug(f"No pruning needed. Current record count: {len(portfolio_ids)}")
                return
            
            # Determine records to delete (oldest ones first)
            records_to_delete = portfolio_ids[:-MAX_PORTFOLIO_RECORDS]
            logger.info(f"Will delete {len(records_to_delete)} old portfolio records")
            
            # Delete old records
            for portfolio_id in records_to_delete:
                self._delete_portfolio_record(portfolio_id)
                
            logger.info(f"Pruning complete. Kept {MAX_PORTFOLIO_RECORDS} most recent records.")
        
        except Exception as e:
            logger.error(f"Error during pruning old records: {str(e)}", exc_info=True)
            # Don't re-raise - pruning failures shouldn't affect the main operation
    
    def _get_all_portfolio_ids(self) -> List[str]:
        """
        Get all portfolio IDs sorted by timestamp (oldest first)
        
        Returns:
            List[str]: List of portfolio IDs sorted by timestamp
        """
        try:
            # Query all portfolio records
            docs = self.vectorstore.similarity_search(
                "portfolio",
                k=1000,  # Large number to get all records
                filter={"type": "portfolio_data"}
            )
            
            # Extract unique portfolio IDs with timestamps
            portfolio_data = {}
            for doc in docs:
                portfolio_id = doc.metadata.get('portfolio_id')
                timestamp = doc.metadata.get('timestamp')
                
                if portfolio_id and timestamp and 'chunk_id' in doc.metadata:
                    portfolio_data[portfolio_id] = timestamp
            
            # Sort by timestamp (oldest first)
            sorted_ids = sorted(portfolio_data.keys(), 
                               key=lambda k: portfolio_data[k])
            
            logger.debug(f"Found {len(sorted_ids)} unique portfolio records")
            return sorted_ids
            
        except Exception as e:
            logger.error(f"Error getting portfolio IDs: {str(e)}", exc_info=True)
            return []
    
    def _delete_portfolio_record(self, portfolio_id: str) -> None:
        """
        Delete a portfolio record and all its chunks from the vector database
        
        Args:
            portfolio_id: ID of the portfolio record to delete
        """
        try:
            logger.debug(f"Deleting portfolio record: {portfolio_id}")
            
            # Get all vector IDs with this portfolio_id
            query_result = self.index.query(
                vector=[0] * self.dimension,  # Dummy vector for metadata-only query
                top_k=100,
                include_metadata=True,
                filter={"portfolio_id": portfolio_id}
            )
            
            # Extract IDs to delete
            ids_to_delete = [match.id for match in query_result.matches]
            
            if not ids_to_delete:
                logger.warning(f"No vectors found for portfolio ID: {portfolio_id}")
                return
                
            # Delete vectors from the index
            self.index.delete(ids=ids_to_delete)
            
            logger.info(f"Successfully deleted portfolio record {portfolio_id} with {len(ids_to_delete)} chunks")
            
        except Exception as e:
            logger.error(f"Error deleting portfolio record {portfolio_id}: {str(e)}", exc_info=True)
    
    async def search_similar_portfolios(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar portfolios using vector similarity with LangChain"""
        try:
            # First try to find complete documents
            complete_docs = self.vectorstore.similarity_search(
                query,
                k=top_k,
                filter={"type": "portfolio_data", "is_complete": True}
            )
            
            # If we found enough complete docs, use those
            if len(complete_docs) >= top_k:
                logger.info(f"Found {len(complete_docs)} complete portfolio documents")
                docs = complete_docs
            else:
                # Otherwise, get a mix of complete and chunked docs
                logger.info(f"Found only {len(complete_docs)} complete docs, searching for additional chunks")
                chunk_docs = self.vectorstore.similarity_search(
                    query,
                    k=top_k * 2,
                    filter={"type": "portfolio_data"}
                )
                docs = complete_docs + chunk_docs
            
            # Process and return results
            similar_portfolios = []
            portfolio_ids_seen = set()
            
            for doc in docs:
                try:
                    # Try to extract portfolio ID to group chunks
                    portfolio_id = doc.metadata.get('portfolio_id')
                    if not portfolio_id or portfolio_id in portfolio_ids_seen:
                        continue
                        
                    # Try to parse JSON
                    try:
                        portfolio_data = json.loads(doc.page_content)
                    except json.JSONDecodeError:
                        # If we can't parse the JSON, try to use the content as raw text
                        logger.warning(f"Could not parse JSON for {portfolio_id}, using raw content")
                        portfolio_data = {"raw_content": doc.page_content}
                    
                    # Add to results
                    similar_portfolios.append({
                        'timestamp': doc.metadata['timestamp'],
                        'portfolio': portfolio_data,
                        'chunk_id': doc.metadata.get('chunk_id')
                    })
                    
                    # Mark this portfolio ID as seen
                    portfolio_ids_seen.add(portfolio_id)
                    
                    # Stop if we have enough results
                    if len(similar_portfolios) >= top_k:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error processing document: {str(e)}")
                    continue
            
            # Sort by timestamp (newest first) and take only the most recent one
            if similar_portfolios:
                similar_portfolios.sort(key=lambda x: x['timestamp'], reverse=True)
                most_recent = [similar_portfolios[0]]
                logger.info(f"Found {len(similar_portfolios)} portfolios, returning only the most recent from {most_recent[0]['timestamp']}")
                return most_recent
            else:
                logger.info("No portfolio data found")
                return []
            
        except Exception as e:
            logger.error(f"Error searching similar portfolios: {str(e)}")
            # Return empty list instead of raising to avoid breaking the agent
            return []
    
    def search_similar_portfolios_sync(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Synchronous version of search_similar_portfolios"""
        try:
            # First try to find complete documents
            complete_docs = self.vectorstore.similarity_search(
                query,
                k=top_k,
                filter={"type": "portfolio_data", "is_complete": True}
            )
            
            # If we found enough complete docs, use those
            if len(complete_docs) >= top_k:
                logger.info(f"Found {len(complete_docs)} complete portfolio documents")
                docs = complete_docs
            else:
                # Otherwise, get a mix of complete and chunked docs
                logger.info(f"Found only {len(complete_docs)} complete docs, searching for additional chunks")
                chunk_docs = self.vectorstore.similarity_search(
                    query,
                    k=top_k * 2,
                    filter={"type": "portfolio_data"}
                )
                docs = complete_docs + chunk_docs
            
            # Process and return results
            similar_portfolios = []
            portfolio_ids_seen = set()
            
            for doc in docs:
                try:
                    # Try to extract portfolio ID to group chunks
                    portfolio_id = doc.metadata.get('portfolio_id')
                    if not portfolio_id or portfolio_id in portfolio_ids_seen:
                        continue
                        
                    # Try to parse JSON
                    try:
                        portfolio_data = json.loads(doc.page_content)
                    except json.JSONDecodeError:
                        # If we can't parse the JSON, try to use the content as raw text
                        logger.warning(f"Could not parse JSON for {portfolio_id}, using raw content")
                        portfolio_data = {"raw_content": doc.page_content}
                    
                    # Add to results
                    similar_portfolios.append({
                        'timestamp': doc.metadata['timestamp'],
                        'portfolio': portfolio_data,
                        'chunk_id': doc.metadata.get('chunk_id')
                    })
                    
                    # Mark this portfolio ID as seen
                    portfolio_ids_seen.add(portfolio_id)
                    
                    # Stop if we have enough results
                    if len(similar_portfolios) >= top_k:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error processing document: {str(e)}")
                    continue
            
            # Sort by timestamp (newest first) and take only the most recent one
            if similar_portfolios:
                similar_portfolios.sort(key=lambda x: x['timestamp'], reverse=True)
                most_recent = [similar_portfolios[0]]
                logger.info(f"Found {len(similar_portfolios)} portfolios, returning only the most recent from {most_recent[0]['timestamp']}")
                return most_recent
            else:
                logger.info("No portfolio data found")
                return []
            
        except Exception as e:
            logger.error(f"Error searching similar portfolios: {str(e)}")
            # Return empty list instead of raising to avoid breaking the agent
            return []
    
    def get_latest_portfolio_data(self) -> Dict[str, Any]:
        """Retrieve the most recent portfolio data from Pinecone"""
        try:
            # Query using LangChain's similarity search with a dummy query
            docs = self.vectorstore.similarity_search(
                "latest portfolio",
                k=1,
                filter={"type": "portfolio_data"}
            )
            
            if not docs:
                return {'holdings': {}}
            
            latest_data = json.loads(docs[0].page_content)
            logger.info("Successfully retrieved latest portfolio data from Pinecone")
            return latest_data
            
        except Exception as e:
            logger.error(f"Error retrieving latest portfolio data: {str(e)}")
            raise
    
    def get_portfolio_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve portfolio history with specified limit from Pinecone"""
        try:
            # Query using LangChain's similarity search
            docs = self.vectorstore.similarity_search(
                "portfolio history",
                k=limit,
                filter={"type": "portfolio_data"}
            )
            
            history = []
            for doc in docs:
                try:
                    portfolio_data = json.loads(doc.page_content)
                    history.append({
                        'timestamp': doc.metadata['timestamp'],
                        'portfolio': portfolio_data
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse portfolio data for chunk {doc.metadata.get('chunk_id')}")
                    continue
            
            logger.info(f"Successfully retrieved {len(history)} portfolio history entries")
            return history
            
        except Exception as e:
            logger.error(f"Error retrieving portfolio history: {str(e)}")
            raise 