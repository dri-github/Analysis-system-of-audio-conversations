pipeline {
    agent any

    environment {
        INT_NETWORK_NAME = 'audio_rec_system_int_net'
        POSTGRES_NETWORK_NAME = 'pg_database_default'

        VOLUME_UPLOADS = '/var/audio_rec_system/uploads'
    }
    
    stages {
        stage('Build Docker Image') {
            steps {
                script {
                    dir('ui') {
                        docker.build("audio_rec_ui", "-f ./Dockerfile .")
                    }
                    dir('backend') {
                        docker.build("audio_rec_api", "-f ./Dockerfile .")
                    }
                    dir('audio_processing') {
                        docker.build("audio_rec_proc", "-f ./Dockerfile .")
                    }
                }
            }
        }
        stage('Run Docker Container') {
            steps {
                sh 'docker stop nginx-gateway'
        
                sh 'docker stop audio_rec_system_proc || true && docker rm audio_rec_system_proc || true'
                sh 'docker stop audio_rec_system_ui || true && docker rm audio_rec_system_ui || true'
                sh 'docker stop audio_rec_system_api || true && docker rm audio_rec_system_api || true'
        
                sh 'docker create --name audio_rec_system_api --network ${POSTGRES_NETWORK_NAME} audio_rec_api'
                sh 'docker create --name audio_rec_system_ui audio_rec_ui'
                sh 'docker create --name audio_rec_system_proc -v ${VOLUME_UPLOADS}:/app/app/audio_uploads audio_rec_proc'
        
                sh 'docker network connect --alias api ${INT_NETWORK_NAME} audio_rec_system_api'
                sh 'docker network connect --alias ui ${INT_NETWORK_NAME} audio_rec_system_ui'
                sh 'docker network connect --alias proc ${INT_NETWORK_NAME} audio_rec_system_proc'
        
                sh 'docker start audio_rec_system_api'
                sh 'docker start audio_rec_system_ui'
                sh 'docker start audio_rec_system_proc'
        
                sh 'docker start nginx-gateway'
            }
        }
    }
}
