# FinPilot Financial Advisor

Your intelligent financial companion for portfolio analysis, market insights, and investment guidance.

## Project Structure

This project consists of two main parts:

1. **Backend (FastAPI)**: Provides the API endpoints and server-side intelligence
2. **Frontend (React with TypeScript)**: Provides the user interface for interacting with the system

The system architecture is organized as follows:

### Backend Organization (`python_backend/`)
- **Core Module**: Configuration management, utility functions, and shared middleware
- **Binance Module**: Portfolio tracking, analysis and reporting for Binance cryptocurrency exchange
- **Kite Module**: Stock portfolio management and performance analysis for Zerodha Kite
- **Finance Query Module**: Smart financial query processing with market data integration

### Frontend Organization (`FinPilot-Frontend/`)
- **React TypeScript Application**: Modern UI with TypeScript support
- **Component-based Architecture**: Reusable UI components in `src/components/`
- **Page-based Structure**: Main application pages in `src/pages/`
- **API Services**: Backend communication layer in `src/services/`
- **Configuration**: Environment-specific settings in `src/config/`
- **Vite Build System**: Fast and efficient build tooling

## Intelligent Agents

The application leverages several intelligent agents for various functions:

- **Binance LangGraph Agent**: A sophisticated agent for analyzing Binance cryptocurrency portfolios
  - [Detailed Documentation](python_backend/binance/agents/query_agent/README.md)

## Setup and Installation

### Backend Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/FinPilot-Financial_Advisor.git
cd FinPilot-Financial_Advisor
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the FastAPI backend:
```bash
python app.py
# or alternatively
uvicorn app:app --reload --port 8000
```

The backend will be available at http://localhost:8000 with API documentation at http://localhost:8000/api/docs.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd FinPilot-Frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000 (or the port specified in your Vite configuration).

## API Features

### Finance Query API
- General financial queries processing via `/api/query`

### Binance Portfolio API
- Portfolio holdings: `/api/binance/portfolio/holdings`
- Portfolio analysis: `/api/binance/portfolio/analysis`
- Custom portfolio queries: `/api/binance/portfolio/query`

### Kite Portfolio API
- Portfolio holdings: `/api/kite/portfolio/holdings`
- Custom portfolio queries: `/api/kite/portfolio/query`

### System API
- Health check: `/api/health`
- Version information: `/api/version`

## Environment Configuration

- Backend configuration is managed through environment variables defined in `.env`
- Frontend configuration for API endpoints is defined in `FinPilot-Frontend/.env`

## API Documentation

When the backend is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## License

[MIT License](LICENSE) 