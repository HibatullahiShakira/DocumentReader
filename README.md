**PitchDeck Processor**
A Flask-based web application for uploading, processing, and analyzing pitch deck files (PDF and PPTX). The app queues uploaded files for processing using Redis, stores metadata in a database, and displays analysis results on a dashboard.

**Features**
File Upload: Upload pitch deck files via a web API (/api/upload).
Supported Formats: Accepts .pdf and .pptx files.
Processing Queue: Uses Redis to queue files for background processing.
Dashboard: View uploaded pitch decks with metadata like slide count, sentiment analysis, and key phrases.
Caching: Dashboard data is cached in Redis for 5 minutes to improve performance.
Error Handling: Returns meaningful error messages for invalid file types or missing files.

**Tech Stack**
Backend: Flask (Python)
Database: SQLAlchemy (with a PitchDeck model)
Queue: Redis
Frontend: HTML templates (e.g., dashboard.html)
Testing: Unit tests with unittest
Prerequisites
Python 3.8+
Redis server
A relational database (e.g., PostgreSQL, SQLite)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/pitchdeck-processor.git
   cd pitchdeck-processor
2. **Create a Virtual Environment**
      ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
3.** Install Dependencies**

      pip install -r requirements.txt
4. **Set Up Environment Variables**
      Create a .env file in the root directory with the following:
         FLASK_APP=app
         FLASK_ENV=development
         DATABASE_URL=sqlite:///pitchdecks.db  # Or your database URL
         REDIS_URL=redis://localhost:6379/0
         UPLOAD_FOLDER=/path/to/uploads
   
5. **Start Redis**
   Ensure a Redis server is running locally or update REDIS_URL to point to your Redis instance:
      ```bash
   redis-server
7. Run the Application
   ```bash
   flask run
