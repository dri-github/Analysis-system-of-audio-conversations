pipeline {
    agent any

    environment {
        INT_NETWORK_NAME = 'audio_rec_system_int_net'
        POSTGRES_NETWORK_NAME = 'pg_database_default'

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
                script {
                    docker.image("audio_rec_api").run("--rm --network ${POSTGRES_NETWORK_NAME}") { c ->
                        sh "docker network connect --alias api ${INT_NETWORK_NAME} ${c.id}"
                    }
                    docker.image("audio_rec_ui").run("--rm --network ${INT_NETWORK_NAME} --network-alias ui")
                    docker.image("audio_rec_proc").run("--rm --network ${INT_NETWORK_NAME} -v ${VOLUME_UPLOADS}:/app/app/audio_uploads")
                }
            }
        }
    }
}
