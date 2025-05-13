# Memoryful Backend

FastAPI backend for Memoryful - Your AI-Powered Life Journal and Analysis Platform

## Overview

Memoryful is an intelligent life journaling platform that combines personal data recording with AI-powered analysis to provide meaningful insights and recommendations for life improvement. The backend serves as the core engine, handling data processing, AI analysis, and integration with various external services.

## Features

### Core Functionality

- **Life Journaling**: Record and organize daily experiences, memories, and activities
- **AI-Powered Analysis**: Automated insights and recommendations using MemoryfulAI
- **External Service Integration**: Seamless connection with health, gaming, and location services
- **Smart Search**: Natural language queries about your life events and patterns
- **Secure Authentication**: JWT-based authentication with email verification

### Data Structure

- **Months**: Track monthly summaries with descriptions and highlights
- **Days**: Detailed daily entries including:
  - Descriptions and content
  - Location data (country/city)
  - Learning progress
  - Custom tags
  - Photo attachments
  - Integration data

### AI Analysis Types

- **Daily Analysis**: Quick insights and notes
- **Weekly Analysis**: Trend identification and pattern recognition
- **Monthly Analysis**: Comprehensive summaries and statistics
- **Yearly Analysis**: Long-term insights and achievements

## Tech Stack

### Backend

- **Framework**: FastAPI
- **Database**: PostgreSQL with Async SQLAlchemy 2.0
- **Caching**: Redis
- **Message Broker**: RabbitMQ
- **Task Queue**: Celery with Flower monitoring
- **Authentication**: JWT (Access + Refresh tokens)
- **API Documentation**: OpenAPI/Swagger

### External Integrations

- Samsung Health (steps and activity data)
- Gaming platforms (Steam, Epic Games, EA)
- Google APIs (location and purchase history)
- Mobile gaming platforms

## Project Structure

```plaintext
memoryful-backend/
├── app/
│   ├── core/               # Core functionality
│   ├── routers/            # API endpoints
│   ├── models/             # Database models
│   ├── schemas/            # Pydantic schemas
│   ├── tasks/              # Celery tasks
│   ├── templates/          # HTML templates (e.g. for email notifications)
│   ├── init_db.py          # Database initialization script
│   └── main.py             # FastAPI application entry point and configuration
├── .env.example            # Example environment variables
├── .gitignore              # Git ignore rules
├── Dockerfile              # Container definition
├── docker-compose.yml      # Container orchestration
├── docker-compose.dev.yml  # Development container config
├── mypy.ini                # MyPy type checking configuration
├── requirements.txt        # Python dependencies
├── requirements.dev.txt    # Development dependencies
└── README.md               # Project documentation
```

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. Clone the repository:

   ```bash
   git clone https://github.com/vlad-proger-rgb/memoryful-backend.git
   cd memoryful-backend
   ```

2. Create and configure environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Build and start all services:

   ```bash
   docker-compose up --build
   ```

The API will be available at `http://localhost:8000`

### Development

For development with hot-reload:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

## API Documentation

Once the server is running, access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Status

This project is currently under active development. The backend is being developed as a solo project, focusing on creating a robust and scalable architecture that can support the complex requirements of the Memoryful platform.
