pipeline {
    agent any

    environment {
        INT_NETWORK_NAME = 'audio_rec_system_int_net'
        POSTGRES_NETWORK_NAME = 'pg_database'

        VOLUME_UPLOADS = '~/uploads'
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
                docker.image("audio_rec_api").runWith("--network-alias api --network ${INT_NETWORK_NAME} --network ${POSTGRES_NETWORK_NAME}")
                docker.image("audio_rec_ui").runWith("--network-alias ui -p 80:3000 --network ${INT_NETWORK_NAME})")
                docker.image("audio_rec_proc").runWith("--network ${INT_NETWORK_NAME} -v ${VOLUME_UPLOADS}:/app/app/audio_uploads")
            }
        }
    }
}
