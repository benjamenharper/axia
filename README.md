# AI-Powered Real Estate Search

A natural language real estate search application similar to Perplexity, allowing users to search for properties using natural language queries.

## Features

- Natural language property search
- Modern, responsive UI
- Real-time search results
- Property cards with images, prices, and details
- Integration with OpenAI for query understanding

## Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file in the backend directory with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

5. Start the backend server:
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The application should now be running at http://localhost:3000

## Usage

1. Enter a natural language query in the search box (e.g., "modern beach house in Maui under 2 million")
2. Click the Search button or press Enter
3. View the matching properties with their details

## Technologies Used

- Backend:
  - FastAPI
  - OpenAI API
  - Python 3.8+

- Frontend:
  - React
  - Chakra UI
  - Axios
