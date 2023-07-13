

# docker ps -a | grep beethon | awk '{print $1}' | xargs docker rm -f
# docker build --no-cache -t beethon .
docker-compose up -d --build 
docker image prune -f