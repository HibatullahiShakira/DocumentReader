# DocumentReader

A Flask-based web application for parsing pitch deck documents (PDF/PPTX) and displaying extracted data in a dashboard.

## Setup Instructions

### Prerequisites
- Python 3.12
- Docker and Docker Compose
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd DocumentReader
   
2. Set up a virtual environment:
   python -m venv .venv
   source .venv/Scripts/activate  # On Windows

3. Install dependencies:
   pip install -r requirements.txt

4. Copy .env.example to .env and update the values:
   cp .env.example .env
   FLASK_ENV=development
   FLASK_DEBUG=1
   SECRET_KEY=
   DATABASE_URL=
   UPLOAD_FOLDER=uploads
   MAX_CONTENT_LENGTH=10485760
   REDIS_URL=
   CELERY_BROKER_URL=
   CELERY_RESULT_BACKEND=

5. Run the app locally
   python app.py

6. Or use docker compose
   docker-compose up --build

7. Run unit tests with:
   pytest