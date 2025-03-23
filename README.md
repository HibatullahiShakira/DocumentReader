# DocumentReader

A web application for parsing and processing pitch deck documents (PDF and PPTX) and displaying the extracted information in a table format.

## Features
- Upload PDF and PPTX files via a REST API.
- Parse documents to extract slide titles, text content, and metadata.
- Store extracted data in a PostgreSQL database.
- Display processed data in a table on a simple dashboard.
- Asynchronous processing using Celery with RabbitMQ and Redis.
- Containerized with Docker and Docker Compose.
- CI/CD pipeline with GitHub Actions to build and push Docker images to Docker Hub.

## Prerequisites
- Docker and Docker Compose
- Python 3.12
- Git
- A Docker Hub account

## Setup and Configuration
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/HibatullahShakira/DocumentReader.git
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