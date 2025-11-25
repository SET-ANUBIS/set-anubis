pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'python -m unittest discover -s tests'
            }
        }
        stage('Build') {
            steps {
                sh 'docker build -t myapp-api:latest -f Dockerfile.api .'
                sh 'docker build -t myapp-streamlit:latest -f Dockerfile.streamlit .'
            }
        }
        stage('Deploy') {
            steps {
                sh 'docker-compose up -d'
            }
        }
    }
}
