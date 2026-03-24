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
│   ├── core/                      # Core functionality
│   ├── routers/                   # API endpoints
│   ├── models/                    # Database models
│   ├── schemas/                   # Pydantic schemas
│   ├── tasks/                     # Celery tasks
│   ├── templates/                 # HTML templates (e.g. for email notifications)
│   ├── init_db.py                 # Database initialization script
│   └── main.py                    # FastAPI application entry point
├── docker/
│   ├── Dockerfile                 # Production container definition
│   ├── Dockerfile.dev             # Development container definition
│   ├── Dockerfile.celery          # Celery worker container definition
│   ├── docker-compose.local.yml   # Local development orchestration
│   ├── docker-compose.prod.yml    # Production orchestration (FastAPI only)
│   └── docker-compose.celery.yml  # Celery worker deployment (for VM)
├── scripts/
│   └── deploy-celery-vm.sh        # Script to create Celery worker VM
├── .env.local                     # Local development environment variables
├── .env.prod                      # Production environment template
├── .gitignore                     # Git ignore rules
├── mypy.ini                       # MyPy type checking configuration
├── requirements.txt               # Python dependencies
├── requirements.dev.txt           # Development dependencies
└── README.md                      # Project documentation
```

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose

### Environment Configurations

This project supports two distinct environments:

#### **Local Development** (`.env.local`)

- All services run locally in Docker containers
- No external dependencies or cloud services
- Uses local PostgreSQL, Redis, RabbitMQ, MinIO, Ollama
- Perfect for development and testing

#### **Production** (`.env.prod`)

- Uses GCP managed services (Cloud SQL, GCS, Pub/Sub)
- Secrets managed via GCP Secret Manager
- Optimized for Cloud Run deployment
- Celery workers run on separate e2-micro VM

### Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/vlad-proger-rgb/memoryful-backend.git
   cd memoryful-backend
   ```

2. Start with docker-compose

   - Local:

   ```bash
   docker-compose -p memoryful -f docker/docker-compose.local.yml --env-file=.env.local up --build
   ```

   - Production using GCP services:

   ```bash
   # First, create .env from template
   cp .env.prod .env
   # Edit .env with your actual values, then run:
   docker-compose -p memoryful -f docker/docker-compose.prod.yml --env-file=.env up --build
   ```

### Production Setup

For production, you'll need to set up the following:

1. Create a GCP project and enable the necessary APIs
2. Set up Cloud SQL, GCS, and Pub/Sub
3. Create secrets in GCP Secret Manager
4. Deploy the application to Cloud Run
5. Redis (e.g., Upstash Redis with free tier)
6. Set up the Celery worker VM

### GCP Secrets

Store these in GCP Secret Manager for production:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `REDIS_HOST`
- `REDIS_PASSWORD`
- `ACCESS_SECRET_KEY`
- `REFRESH_SECRET_KEY`
- `RESEND_API_KEY`
- `MAIL_FROM`
- `S3_ACCESS_KEY_ID` (for GCS)
- `S3_SECRET_ACCESS_KEY` (for GCS)
- `OPENAI_API_KEY` (if using OpenAI)
- `ANTHROPIC_API_KEY` (if using Anthropic)

## API Documentation

Once the server is running, access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Status

This project is currently under active development. The backend is being developed as a solo project, focusing on creating a robust and scalable architecture that can support the complex requirements of the Memoryful platform.
