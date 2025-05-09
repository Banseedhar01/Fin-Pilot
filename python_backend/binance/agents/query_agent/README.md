# Binance Portfolio LangGraph Agent

A sophisticated agent built with LangGraph and LangChain for answering queries about a user's Binance cryptocurrency portfolio using RAG (Retrieval Augmented Generation) and optional web search.

## Features

- **RAG-based retrieval**: Uses vector database (Pinecone) to fetch relevant portfolio data based on user queries
- **Intelligent query classification**: Determines if a query needs real-time web data or can be answered from historical portfolio data
- **Web search integration**: Uses Tavily API to fetch real-time market data when needed
- **LangGraph workflow**: Orchestrates the entire process with a clear, traceable execution flow
- **Robust error handling**: Comprehensive error handling at each step of the process
- **Async support**: Full asynchronous execution support

## Architecture

The agent uses a LangGraph workflow with the following nodes:

1. **Query Classification**: Analyzes the query to determine if web search is needed
2. **Context Retrieval**: Retrieves relevant portfolio data from vector database
3. **Web Search**: Performs web search for real-time market data (conditional)
4. **Response Generation**: Generates a comprehensive response combining portfolio data and web search results

### Agent Flow Diagram

<pre> ```mermaid flowchart TD Start([Start]) Classify[classify_query] Retrieve[retrieve_context] Decision{_should_search_web?} Search[search_web] Generate[generate_response] End([End]) Start --> Classify Classify --> Retrieve Retrieve --> Decision Decision -- True --> Search Decision -- False --> Generate Search --> Generate Generate --> End ``` </pre>

```
┌───────────────────┐
│                   │
│    User Query     │
│                   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Classify Query   │
│                   │
│ Determine if web  │
│ search is needed  │
│                   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Retrieve Context  │
│                   │
│  Vector DB RAG    │
│  for portfolio    │
│     data          │
│                   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐              ┌───────────────────┐
│   Decision Node   │     Yes      │   Search Web      │
│                   ├─────────────►│                   │
│  Needs web search?│              │ Tavily Search API │
│                   │              │ for market data   │
└─────────┬─────────┘              └─────────┬─────────┘
          │ No                               │
          │                                  │
          ▼                                  ▼
┌─────────────────────────────────────────────────────┐
│                                                     │
│               Generate Response                     │
│                                                     │
│  Combine portfolio data and market information      │
│  to create comprehensive answer using LLM           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Technical Implementation Details

The LangGraph agent is implemented using the following components:

- **StateGraph**: The core LangGraph component that orchestrates the workflow
- **AgentState**: A TypedDict maintaining the state throughout execution
- **Conditional Edges**: Dynamic routing based on query classification results
- **LangChain Tools**: Integration with Tavily search and vector database retrieval

The graph is constructed in the `_create_graph` method:

```python
workflow = StateGraph(AgentState)
workflow.add_node("classify_query", self._classify_query)
workflow.add_node("retrieve_context", self._retrieve_context)
workflow.add_node("search_web", self._search_web)
workflow.add_node("generate_response", self._generate_response)

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
```

## Usage

```python
from python_backend.binance.agents.query_agent import BinanceLangGraphAgent

# Initialize the agent
agent = BinanceLangGraphAgent()

# Process a query synchronously
result = agent.process_query("What's the performance of my portfolio in the last month?")
print(result["response"])

# Process a query asynchronously
result = await agent.process_query_async("How much have I invested in futures?")
print(result["response"])
```

## Requirements

- OpenAI API key (GPT-3.5-turbo or above)
- Tavily API key (for web search)
- Pinecone vector database with portfolio data

## Integration with Existing Systems

The agent integrates with:

- **Portfolio Manager**: To access and analyze portfolio data
- **Vector DB Storage**: To retrieve semantic matches for queries
- **Tavily Search**: For real-time market data when needed

## Error Handling

The agent handles errors gracefully at each step of the process, ensuring that failures in one component (e.g., web search) don't prevent the agent from providing a response based on available data.

## State Management

The LangGraph workflow maintains a complete state throughout execution:

```python
{
    "query": str,                  # Original user query
    "context": List[str],          # Retrieved portfolio context
    "needs_web_search": bool,      # Whether web search is needed
    "web_search_results": str,     # Results from web search
    "response": str,               # Final generated response
    "chat_history": List[Dict],    # Chat history for context
    "error": Optional[str]         # Error message if any
}
```

This allows for transparent reasoning and debugging of the agent's decision process.

## Performance Considerations

- The agent is designed to minimize API calls when possible
- Caching mechanisms can be implemented for frequent queries
- Response time varies based on whether web search is required

## Future Enhancements

- Integration with additional market data sources
- Support for multi-exchange portfolio analysis
- Advanced portfolio optimization recommendations
- Historical trend analysis and visualization 