pipeline {
    agent any
    stages {
        stage('Build Docker Image') {
            steps {
                script {
                    dir('ui') {
                        docker.build("ar_ui", "-f ./Dockerfile .")
                    }
                    dir('backend') {
                        docker.build("ar_back", "-f ./Dockerfile .")
                    }
                    dir('audio_processing') {
                        docker.build("ar_audio_proc", "-f ./Dockerfile .")
                    }
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
