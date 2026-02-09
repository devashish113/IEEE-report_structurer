// Jenkinsfile for IEEE Report Restructurer
// CI/CD Pipeline for building, testing, and deploying the application

pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'ieee-report-restructurer'
        DOCKER_TAG = "${BUILD_NUMBER}"
        REGISTRY = 'your-registry.com'  // Change to your Docker registry
        GROQ_API_KEY = credentials('groq-api-key')  // Store in Jenkins credentials
    }
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Checked out branch: ${env.BRANCH_NAME ?: 'main'}"
            }
        }
        
        stage('Environment Setup') {
            steps {
                script {
                    // Create .env file for Docker build
                    writeFile file: '.env', text: """
GROQ_API_KEY=${GROQ_API_KEY}
GROQ_MODEL=llama-3.1-8b-instant
"""
                }
            }
        }
        
        stage('Lint & Code Quality') {
            steps {
                echo 'Running code quality checks...'
                script {
                    // Optional: Add linting steps
                    sh '''
                        # Install linting tools if needed
                        pip install ruff --quiet || true
                        
                        # Run Python linting
                        ruff check backend/app --ignore E501 || echo "Linting warnings found"
                    '''
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo 'Building Docker image...'
                script {
                    docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}")
                    docker.build("${DOCKER_IMAGE}:latest")
                }
            }
        }
        
        stage('Test') {
            steps {
                echo 'Running tests...'
                script {
                    sh '''
                        # Run container tests
                        docker run --rm ${DOCKER_IMAGE}:${DOCKER_TAG} python -c "from app.main import app; print('Import test passed')"
                        
                        # Health check test
                        docker run -d --name test-container -p 8080:8000 ${DOCKER_IMAGE}:${DOCKER_TAG}
                        sleep 10
                        curl -f http://localhost:8080/health || exit 1
                        docker stop test-container
                        docker rm test-container
                    '''
                }
            }
        }
        
        stage('Security Scan') {
            steps {
                echo 'Running security scan...'
                script {
                    // Optional: Add security scanning
                    sh '''
                        # Trivy scan (if installed)
                        trivy image ${DOCKER_IMAGE}:${DOCKER_TAG} --exit-code 0 --severity HIGH,CRITICAL || echo "Security scan complete"
                    '''
                }
            }
        }
        
        stage('Push to Registry') {
            when {
                branch 'main'
            }
            steps {
                echo 'Pushing to Docker registry...'
                script {
                    docker.withRegistry("https://${REGISTRY}", 'docker-registry-credentials') {
                        docker.image("${DOCKER_IMAGE}:${DOCKER_TAG}").push()
                        docker.image("${DOCKER_IMAGE}:latest").push()
                    }
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                echo 'Deploying to staging environment...'
                script {
                    sh '''
                        # Deploy to staging
                        docker-compose -f docker-compose.yml down || true
                        docker-compose -f docker-compose.yml up -d
                        
                        # Wait for health check
                        sleep 15
                        curl -f http://localhost:8000/health
                    '''
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production environment...'
                script {
                    // Add production deployment steps
                    sh '''
                        # Example: Deploy using docker-compose with production profile
                        docker-compose -f docker-compose.yml --profile production down || true
                        docker-compose -f docker-compose.yml --profile production up -d
                        
                        # Health check
                        sleep 20
                        curl -f http://localhost:8000/health
                    '''
                }
            }
        }
    }
    
    post {
        always {
            echo 'Cleaning up...'
            script {
                // Clean up Docker images
                sh '''
                    docker image prune -f || true
                '''
            }
        }
        success {
            echo 'Pipeline completed successfully!'
            // Optional: Send notification
            // slackSend(color: 'good', message: "Build ${BUILD_NUMBER} succeeded!")
        }
        failure {
            echo 'Pipeline failed!'
            // Optional: Send notification
            // slackSend(color: 'danger', message: "Build ${BUILD_NUMBER} failed!")
        }
    }
}
