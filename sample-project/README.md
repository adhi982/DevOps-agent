# DevOps Pipeline Demo Application

A simple Flask web application designed to demonstrate a complete DevOps CI/CD pipeline with automated testing, linting, building, and security scanning.

## Features

- **Web API**: RESTful Flask application with multiple endpoints
- **Calculator Service**: Basic mathematical operations API
- **Health Monitoring**: Health check and application info endpoints
- **Error Handling**: Comprehensive error handling and validation
- **Security**: Following security best practices
- **Testing**: Complete test suite with pytest
- **Containerization**: Docker support for easy deployment

## Project Structure

```
sample-project/
├── app.py              # Main Flask application
├── utils.py            # Utility functions and helpers
├── test_app.py         # Tests for main application
├── test_utils.py       # Tests for utility functions
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container configuration
├── .env.example       # Environment variables template
└── README.md          # This file
```

## API Endpoints

### GET /
Home endpoint returning welcome message and status.

### GET /health
Health check endpoint for monitoring.

### GET /info
Application information and available endpoints.

### POST /calculate
Perform mathematical calculations.

**Request Body:**
```json
{
  "operation": "add|subtract|multiply|divide",
  "num1": 10,
  "num2": 5
}
```

**Response:**
```json
{
  "operation": "add",
  "num1": 10,
  "num2": 5,
  "result": 15,
  "timestamp": "2025-06-27T00:00:00"
}
```

## Setup and Installation

### Local Development

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd sample-project
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`.

### Docker Deployment

1. **Build Docker image:**
   ```bash
   docker build -t devops-demo-app .
   ```

2. **Run container:**
   ```bash
   docker run -p 5000:5000 devops-demo-app
   ```

## Testing

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file:
```bash
pytest test_app.py
pytest test_utils.py
```

## Code Quality

### Linting with pylint:
```bash
pylint app.py utils.py
```

### Formatting with black:
```bash
black app.py utils.py test_*.py
```

### Type checking with mypy:
```bash
mypy app.py utils.py
```

## DevOps Pipeline

This project is designed to work with the DevOps Orchestrator pipeline, which includes:

1. **Lint Stage**: Code quality checks with pylint and flake8
2. **Test Stage**: Automated testing with pytest and coverage reporting
3. **Build Stage**: Docker image building and validation
4. **Security Stage**: Security vulnerability scanning

### Pipeline Requirements Met:

- ✅ **Python files (.py)**: app.py, utils.py
- ✅ **requirements.txt**: Python dependencies
- ✅ **Dockerfile**: Container configuration
- ✅ **Test files**: test_app.py, test_utils.py
- ✅ **Proper docstrings**: All functions documented
- ✅ **Error handling**: Comprehensive exception handling
- ✅ **Security practices**: Non-root user, input validation

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | Flask secret key | dev-secret-key |
| DEBUG | Enable debug mode | False |
| PORT | Application port | 5000 |
| DATABASE_URL | Database connection string | sqlite:///app.db |
| API_BASE_URL | External API base URL | https://api.example.com |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions or issues, please open an issue in the repository or contact the development team.
