# Frontend Integration Setup

This guide explains how to build and run the Newsloom application with the integrated frontend from https://github.com/rimamedia/newsloom-frontend.

## Prerequisites

- Git with SSH access configured for GitHub
- Node.js and npm
- Docker
- Access to the newsloom-frontend repository

## Development Workflow

### 1. Build Frontend

The frontend build process is separated from the Docker build for better caching and faster development cycles.

```bash
# Make the build script executable (if not already)
chmod +x build-frontend.sh

# Run the build script with default branch (main)
./build-frontend.sh

# Or specify a different branch
./build-frontend.sh develop
./build-frontend.sh feature/new-login
```

This script will:
- Clone the frontend repository
- Install dependencies
- Create development environment configuration
- Build the frontend
- Copy built files to frontend-dist/

### 2. Build and Run with Docker Compose

After the frontend is built, you can use Docker Compose to run the entire stack:

```bash
# Build and start the services
docker-compose -f docker-compose.frontend.yml up --build

# To run in detached mode
docker-compose -f docker-compose.frontend.yml up -d

# To stop the services
docker-compose -f docker-compose.frontend.yml down
```

The application will be available at:
- Frontend: http://localhost
- API: http://localhost/api/
- Admin: http://localhost/admin/
- WebSocket: ws://localhost/ws/

### Environment Configuration

The development environment uses these default settings:
- API URL: http://localhost
- WebSocket URL: ws://localhost/ws
- Base URL: http://localhost

Additional environment variables for the backend are configured in docker-compose.frontend.yml:
- Database configuration
- Django settings
- CSRF settings

To modify these settings, edit the environment variables in `build-frontend.sh` before running the build.

### File Structure

- `build-frontend.sh`: Script to build the frontend
- `Dockerfile.frontend`: Docker configuration for the integrated application
- `nginx.frontend.conf`: Nginx configuration for serving the frontend and proxying requests
- `docker-compose.frontend.yml`: Docker Compose configuration for the full stack
- `frontend-dist/`: Directory containing the built frontend files (created by build script)

### Development Tips

1. For frontend-only changes:
   - Make changes in the frontend repository
   - Run `./build-frontend.sh`
   - Rebuild and restart the Docker container

2. For backend-only changes:
   - Make changes to the Django application
   - Rebuild and restart the Docker container

3. For full-stack development:
   - Run the frontend development server separately (from frontend repository)
   - Run the backend server separately
   - Use the frontend dev server for rapid frontend development

### Troubleshooting

1. If the build script fails:
   - Check SSH access to GitHub
   - Verify Node.js and npm are installed
   - Check for sufficient disk space

2. If the Docker Compose build fails:
   - Verify frontend was built successfully (frontend-dist/ exists)
   - Check Docker daemon is running
   - Review build logs: `docker-compose -f docker-compose.frontend.yml logs`

3. If the application doesn't work:
   - Check container logs: `docker logs <container-id>`
   - Verify all services are running inside container
   - Check nginx configuration and logs
