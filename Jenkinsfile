pipeline {
    agent any

    environment {
        VENV = "venv"
    }

    stages {

        stage('Clone Repository') {
            steps {
                echo 'Cloning backend repository...'
            }
        }

        stage('Setup Python Environment') {
            steps {
                sh '''
                python3 -m venv $VENV
                . $VENV/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Basic Check') {
            steps {
                sh '''
                . $VENV/bin/activate
                python --version
                '''
            }
        }
    }

    post {
        success {
            echo 'Backend pipeline executed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}

stage('Deploy Backend') {
    steps {
        sh '''
        pkill -f uvicorn || true
        nohup venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &
        '''
    }
}
