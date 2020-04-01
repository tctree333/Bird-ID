echo "Starting Local Redis Server"
bash ./install-redis.sh
redis-server &
export SCIOLY_ID_BOT_LOCAL_REDIS="true"
echo "Redis Server Started"
