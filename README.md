# Pitch Deck Parser

## Overview
A Flask-based web application that parses pitch deck documents (PDF or PPTX files), performs sentiment analysis, and stores extracted information in PostgreSQL. The application uses Redis for caching dashboard data and queuing file processing tasks.

## Features
- File upload with validation (PDF/PPTX only, 10MB max)
- Document parsing using PyPDF2 and python-pptx
- Sentiment analysis using NLTK's VADER
- PostgreSQL storage for extracted data
- Redis for caching dashboard data and queuing file processing
- Separate worker service for asynchronous processing
- Basic dashboard interface with separated CSS and JavaScript
- Error handling for file uploads, database connections, and parsing
- Unit tests for critical functionalities

## Prerequisites
- Docker
- Docker Compose
- GitHub account with Docker Hub integration

## Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pitch-deck-parser