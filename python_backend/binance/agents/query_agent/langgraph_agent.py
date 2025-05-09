from typing import Dict, Any, List, Union, TypedDict, Annotated, Sequence
import logging
import os
import traceback
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.runnables.base import RunnableSerializable
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from ...vectordb_storage.storage import VectorDBStorage
from ....core.logger import setup_logger

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = setup_logger(__name__)

# Define the state schema
class AgentState(TypedDict):
    """Schema for the agent state"""
    query: str
    context: List[str]
    needs_web_search: bool
    web_search_results: str
    response: str
    chat_history: List[Dict[str, str]]
    error: Union[str, None]

class BinanceLangGraphAgent:
    """
    A LangGraph-based agent for answering Binance portfolio queries
    using RAG and optional web search
    """
    
    def __init__(self, vector_storage=None):
        """
        Initialize the Binance LangGraph agent
        
        Args:
            vector_storage: Optional VectorDBStorage instance (if not provided, a new one will be created)
        """
        try:
            logger.info("Initializing BinanceLangGraphAgent...")
            
            # Initialize OpenAI for language processing
            self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            
            # Use provided vector storage or create new one
            self.vector_storage = vector_storage or VectorDBStorage()
            
            # Initialize Tavily search
            tavily_api_key = os.getenv("TAVILY_API_KEY", "")
            if not tavily_api_key:
                logger.warning("TAVILY_API_KEY environment variable is not set. Web search will likely fail.")
            else:
                logger.info(f"Using Tavily API key: {tavily_api_key[:4]}...{tavily_api_key[-4:] if len(tavily_api_key) > 8 else ''}")
                
            try:
                self.web_search_tool = TavilySearchResults(
                    api_key=tavily_api_key,
                    max_results=3
                )
                logger.info("Tavily search tool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily search: {str(e)}")
                # Create a fallback search tool that returns a friendly error message
                self.web_search_tool = lambda query: [{"source": "Error", "title": "Search Unavailable", "content": f"Web search is currently unavailable: {str(e)}"}]
            
            # Create and compile the graph
            self.graph = self._create_graph()
            
            logger.info("BinanceLangGraphAgent initialized successfully")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Error initializing BinanceLangGraphAgent: {str(e)}")
            logger.error(f"Traceback: {error_trace}")
            raise
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow for the agent"""
        logger.info("Creating LangGraph workflow...")
        
        # Define the graph with the agent state
        workflow = StateGraph(AgentState)
        
        # Add nodes to the graph
        workflow.add_node("classify_query", self._classify_query)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("search_web", self._search_web)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges to direct the flow
        workflow.add_edge("classify_query", "retrieve_context")
        workflow.add_conditional_edges(
            "retrieve_context",
            self._should_search_web,
            {
                True: "search_web",
                False: "generate_response"
            }
        )
        workflow.add_edge("search_web", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # Set entry point
        workflow.set_entry_point("classify_query")
        
        logger.info("LangGraph workflow created and compiled")
        return workflow.compile()
    
    def _classify_query(self, state: AgentState) -> AgentState:
        """Classify the query to determine if it requires web search"""
        try:
            logger.info(f"Classifying query: {state['query']}")
            
            # Template for classifying the query
            template = """
            You are analyzing a query about a cryptocurrency portfolio on Binance.
            Determine if this query likely requires up-to-date market information or external data 
            that might not be in the historical portfolio data.
            
            Query: {query}
            
            If the query is about current market conditions, price predictions, news, or anything 
            that requires real-time or external information, respond with "NEEDS_WEB_SEARCH".
            
            If the query is only about historical portfolio data, holdings, past performance, or account information
            that would be contained in portfolio records, respond with "PORTFOLIO_DATA_ONLY".
            
            Your response (NEEDS_WEB_SEARCH or PORTFOLIO_DATA_ONLY):
            """
            
            prompt = PromptTemplate.from_template(template)
            
            # Create chain to classify query
            classify_chain = prompt | self.llm | StrOutputParser()
            
            # Execute chain
            classification = classify_chain.invoke({"query": state["query"]})
            
            # Update state
            new_state = state.copy()
            new_state["needs_web_search"] = "NEEDS_WEB_SEARCH" in classification
            
            logger.info(f"Query classified as: {'NEEDS_WEB_SEARCH' if new_state['needs_web_search'] else 'PORTFOLIO_DATA_ONLY'}")
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error in _classify_query: {str(e)}")
            new_state = state.copy()
            new_state["error"] = f"Error classifying query: {str(e)}"
            return new_state
    
    def _retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from vector DB"""
        try:
            logger.info("Retrieving context from vector DB")
            
            # Use the synchronous version of the search method
            similar_portfolios = self.vector_storage.search_similar_portfolios_sync(state["query"], top_k=1)
            
            # Extract context from results
            context = []
            if similar_portfolios:
                for item in similar_portfolios:
                    timestamp = item["timestamp"]
                    portfolio_data = item["portfolio"]
                    
                    # Format the portfolio data for better readability
                    formatted_data = json.dumps(portfolio_data, indent=2)
                    
                    # Add clear indication that this is the latest data
                    context.append(f"LATEST PORTFOLIO DATA (as of {timestamp}):\n{formatted_data}")
                    
                    logger.info(f"Using portfolio data from {timestamp}")
            
            # Update state
            new_state = state.copy()
            new_state["context"] = context
            
            logger.info(f"Retrieved {len(context)} portfolio records as context")
            
            # Add fallback message if no context was found
            if not context:
                logger.warning("No portfolio records found, adding fallback message")
                new_state["context"] = ["No relevant portfolio data was found. The system may need more portfolio data to answer this query effectively."]
            
            return new_state
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Error in _retrieve_context: {str(e)}")
            logger.error(f"Traceback: {error_trace}")
            new_state = state.copy()
            new_state["error"] = f"Error retrieving context: {str(e)}"
            new_state["context"] = ["Could not retrieve portfolio data due to an error."]
            return new_state
    
    def _should_search_web(self, state: AgentState) -> bool:
        """Determine if web search is needed"""
        return state.get("needs_web_search", False)
    
    def _search_web(self, state: AgentState) -> AgentState:
        """Search the web for additional information"""
        try:
            logger.info(f"Performing web search for: {state['query']}")
            
            # Augment query with crypto context if necessary
            search_query = state["query"]
            if not any(term in search_query.lower() for term in ["crypto", "bitcoin", "binance", "cryptocurrency"]):
                search_query += " cryptocurrency binance"
            
            # Perform web search
            try:
                # Check if web_search_tool is a callable (like our lambda fallback)
                if callable(self.web_search_tool) and not hasattr(self.web_search_tool, 'invoke'):
                    search_results = self.web_search_tool(search_query)
                else:
                    search_results = self.web_search_tool.invoke(search_query)
                    
                logger.info(f"Search returned results of type {type(search_results)}")
            except Exception as search_ex:
                logger.error(f"Error during web search execution: {str(search_ex)}")
                search_results = [{"source": "Error", "title": "Search Failed", 
                                   "content": f"Web search tool error: {str(search_ex)}"}]
            
            # Format the results with safe access to fields
            formatted_results = []
            
            # Check if search_results is a list
            if isinstance(search_results, list):
                for result in search_results:
                    # Safely access fields with fallbacks
                    source = result.get('source', 'Unknown source')
                    title = result.get('title', 'No title')
                    content = result.get('content', result.get('snippet', 'No content available'))
                    
                    formatted_results.append(f"Source: {source}\nTitle: {title}\nContent: {content}\n")
            else:
                # Handle non-list results
                logger.warning(f"Unexpected search results format: {type(search_results)}")
                formatted_results.append(f"Search resulted in unexpected format: {str(search_results)[:200]}...")
            
            # Join the formatted results
            formatted_text = "\n".join(formatted_results) if formatted_results else "No relevant search results found."
            
            # Update state
            new_state = state.copy()
            new_state["web_search_results"] = formatted_text
            
            logger.info("Web search completed successfully")
            
            return new_state
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Error in _search_web: {str(e)}")
            logger.error(f"Search error traceback: {error_trace}")
            new_state = state.copy()
            new_state["error"] = f"Error searching web: {str(e)}"
            new_state["web_search_results"] = "Web search failed, proceeding with available portfolio data only."
            return new_state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate a response based on the context and web search results"""
        try:
            logger.info("Generating response")
            
            # Prepare context
            portfolio_context = "\n\n".join(state.get("context", []))
            web_context = state.get("web_search_results", "")
            
            # Template for generating a response
            template = """
            You are a financial advisor specializing in cryptocurrency and Binance portfolios.
            Provide a detailed and helpful response to the user's query based on the information provided.
            
            User Query: {query}
            
            Portfolio Data:
            {portfolio_context}
            
            {web_search_section}
            
            Provide a clear, concise response that directly addresses the user's question.
            Include specific data points from the portfolio when relevant.
            If the information provided is insufficient to answer fully, acknowledge limitations.
            
            Important guidelines:
            - Explicitly mention that your analysis is based on the most recent available portfolio data
            - Present only the data from the latest snapshot, don't reference multiple timestamps
            - Be concise but thorough in your answer
            
            Be helpful, professional, and accurate in your response.
            """
            
            # Include web search section only if it exists
            if web_context:
                web_search_section = f"Web Search Results:\n{web_context}"
            else:
                web_search_section = "No external data was needed to answer this query."
            
            prompt = PromptTemplate.from_template(template)
            
            # Create chain to generate response
            response_chain = (
                prompt | 
                self.llm | 
                StrOutputParser()
            )
            
            # Execute chain
            response = response_chain.invoke({
                "query": state["query"],
                "portfolio_context": portfolio_context if portfolio_context else "No relevant portfolio data found.",
                "web_search_section": web_search_section
            })
            
            # Update state
            new_state = state.copy()
            new_state["response"] = response
            
            # Update chat history
            chat_history = state.get("chat_history", [])
            chat_history.append({"role": "user", "content": state["query"]})
            chat_history.append({"role": "assistant", "content": response})
            new_state["chat_history"] = chat_history
            
            logger.info("Response generated successfully")
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error in _generate_response: {str(e)}")
            new_state = state.copy()
            new_state["error"] = f"Error generating response: {str(e)}"
            new_state["response"] = "I'm sorry, I encountered an error while generating a response. Please try again."
            return new_state
    
    def _is_simple_query(self, query: str) -> bool:
        """
        Use LLM to determine if the query is a simple greeting or small talk 
        that doesn't require portfolio data or web search
        """
        try:
            # Template for query classification
            template = """
            You are analyzing a user query sent to a cryptocurrency portfolio assistant.
            Determine if this query is a simple greeting, small talk, or general question that doesn't
            require looking up specific portfolio data or searching the web.

            Query: "{query}"

            Examples of simple queries that don't need data lookup:
            - "Hello there"
            - "How are you?"
            - "What can you help me with?"
            - "What can you do?"
            - "Tell me about yourself"
            - "Who made you?"

            Examples of queries that DO require data lookup:
            - "How is my portfolio doing?"
            - "What's the value of my Bitcoin?"
            - "Show me my holdings"
            - "What's the current price of Ethereum?"
            - "Has my portfolio grown this month?"

            Respond with exactly "SIMPLE" if the query is simple small talk or general information,
            or "COMPLEX" if it requires portfolio data or web search.

            Your response (SIMPLE or COMPLEX):
            """
            
            # Create chain to classify
            prompt = PromptTemplate.from_template(template)
            classify_chain = prompt | self.llm | StrOutputParser()
            
            # Execute chain
            classification = classify_chain.invoke({"query": query})
            
            # Determine if simple
            is_simple = "SIMPLE" in classification
            
            logger.info(f"Query '{query}' classified as: {'SIMPLE' if is_simple else 'COMPLEX'}")
            return is_simple
            
        except Exception as e:
            # If any error occurs in classification, assume it's not a simple query
            logger.warning(f"Error determining if query is simple: {str(e)}. Treating as complex.")
            return False
    
    def _get_simple_response(self, query: str) -> Dict[str, Any]:
        """Generate a dynamic response for simple queries using the LLM"""
        try:
            # Template for generating responses to simple queries
            template = """
            You are a helpful cryptocurrency portfolio assistant for Binance users.
            Respond professionally but conversationally to this simple query.
            
            Query: "{query}"
            
            Your response should:
            - Be friendly and helpful
            - Be concise (no more than 3 sentences)
            - Not request or reference any specific portfolio data
            - Mention that you can help with cryptocurrency portfolio analysis if relevant
            
            Your response:
            """
            
            prompt = PromptTemplate.from_template(template)
            response_chain = prompt | self.llm | StrOutputParser()
            
            # Generate the response
            response = response_chain.invoke({"query": query})
            logger.info(f"Generated simple response for query: '{query}'")
            
            return {
                "status": "success",
                "response": response,
                "chat_history": [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": response}
                ]
            }
        except Exception as e:
            logger.error(f"Error generating simple response: {str(e)}")
            
            # Fallback to standard greeting
            fallback = "Hello! I'm your Binance portfolio assistant. I can help you with information about your cryptocurrency holdings, portfolio performance, and market trends. How can I assist you today?"
            
            return {
                "status": "success",
                "response": fallback,
                "chat_history": [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": fallback}
                ]
            }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query using the LangGraph workflow
        (This method replaces the old process_query_async method)
        
        Args:
            query: The user's query about their Binance portfolio
            
        Returns:
            Dict containing the response and status
        """
        try:
            logger.info(f"Processing query: '{query}'")
            
            # Check if the query is just a greeting
            if self._is_simple_query(query):
                logger.info("Detected simple query, generating direct response")
                return self._get_simple_response(query)
            
            # Initialize state
            initial_state: AgentState = {
                "query": query,
                "context": [],
                "needs_web_search": False,
                "web_search_results": "",
                "response": "",
                "chat_history": [],
                "error": None
            }
            
            # Invoke the graph synchronously
            result = self.graph.invoke(initial_state)
            
            # Check for errors
            if result.get("error"):
                logger.error(f"Error in graph execution: {result['error']}")
                return {
                    "status": "error",
                    "message": result["error"],
                    "response": result.get("response", "I encountered an error processing your query.")
                }
            
            logger.info(f"Query processed successfully")
            return {
                "status": "success",
                "response": result["response"],
                "chat_history": result.get("chat_history", [])
            }
                
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Error processing query: {str(e)}")
            logger.error(f"Traceback: {error_trace}")
            return {
                "status": "error",
                "message": f"Error processing query: {str(e)}",
                "response": "I'm sorry, I encountered an error while processing your query. Please try again."
            } 