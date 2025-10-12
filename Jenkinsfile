pipeline {
    agent any
    stages {
        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("ar_ui", "-f ui/Dockerfile .")
                }
            }
        }
        stage('Run Docker Container') {
            steps {
                sh 'echo Success'
            }
        }
    }
}
