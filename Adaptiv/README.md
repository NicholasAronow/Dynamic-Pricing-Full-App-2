# Adaptiv - Dynamic Pricing Platform

Adaptiv is a modern web application for dynamic pricing and business intelligence, built with React (TypeScript) frontend and FastAPI backend.

## Tech Stack

### Frontend
- React with TypeScript
- Ant Design (UI component library)
- React Router for navigation
- Axios for API requests

### Backend
- FastAPI (Python-based high-performance web framework)
- SQLAlchemy ORM
- PostgreSQL database
- JWT Authentication

## Features

- User authentication (login/signup)
- Business profile management
- Dashboard with pricing analytics visualizations
- Competitor analysis tools

## Project Structure

```
adaptiv/
├── backend/            # FastAPI backend
│   ├── main.py         # Main entry point
│   ├── database.py     # Database connection
│   ├── models.py       # SQLAlchemy models
│   ├── schemas.py      # Pydantic schemas
│   ├── auth.py         # Authentication routes
│   ├── profile.py      # Profile routes
│   └── requirements.txt # Python dependencies
├── frontend/           # React frontend
│   ├── public/
│   └── src/
│       ├── components/ # React components
│       ├── context/    # React context (auth)
│       ├── services/   # API services
│       └── ...
└── README.md           # Project documentation
```

## Local Development Setup

### Prerequisites

- Python 3.8+ (for backend)
- Node.js 16+ and npm/yarn (for frontend)
- PostgreSQL database (or use SQLite for development)

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the backend directory with the following content (adjust as needed):
   ```
   DATABASE_URL=postgresql://postgres:password@localhost/adaptiv
   SECRET_KEY=your_secure_secret_key_here
   ```

6. Run the backend server:
   ```
   uvicorn main:app --reload
   ```

7. The API will be available at http://localhost:8000 and the automatic API documentation at http://localhost:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm start
   ```

4. The frontend will be available at http://localhost:3000

## Deployment

For production deployment:

1. Build the frontend:
   ```
   cd frontend
   npm run build
   ```

2. Set up a production database (PostgreSQL recommended)
3. Configure your environment variables for production
4. Deploy the FastAPI backend using Gunicorn + Uvicorn workers
5. Serve the React frontend build using Nginx or a similar web server

## License

[MIT License](LICENSE)
