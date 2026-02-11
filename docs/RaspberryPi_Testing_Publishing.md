sudo git clone https://github.com/BBultitude/DockerMate.git


docker stop dockermate && docker rm dockermate

sudo mkdir -p /srv/sda1/Appdata/DockerMate/{data,stacks,exports}
sudo chown -R 1000:1000 /srv/sda1/Appdata/DockerMate
sudo chmod -R 755 /srv/sda1/Appdata/DockerMate
ls -la /srv/sda1/Appdata/DockerMate/


sudo docker run -d --name dockermate --restart unless-stopped --group-add $(getent group docker | cut -d: -f3) -p 5000:5000 -v /var/run/docker.sock:/var/run/docker.sock:ro -v /srv/sda1/Appdata/DockerMate/data:/app/data -v /srv/sda1/Appdata/DockerMate/stacks:/app/stacks -v /srv/sda1/Appdata/DockerMate/exports:/app/exports -e TZ=Australia/Brisbane -e DOCKERMATE_SSL_MODE=self-signed -e DOCKERMATE_SESSION_EXPIRY=8h -e DOCKERMATE_REMEMBER_ME_EXPIRY=7d dockermate:latest






echo  | docker login ghcr.io -u BBultitude --password-stdin


docker tag 8c7b60147443 ghcr.io/bbultitude/dockermate:latest

docker push ghcr.io/bbultitude/dockermate:latest
docker tag 8c7b60147443 ghcr.io/bbultitude/dockermate:1.0.0-rc1

docker push ghcr.io/bbultitude/dockermate:1.0.0-rc1