echo "Starting Local Redis Server"
bash ./install-redis.sh
redis-server &
export LOCAL_REDIS="true"
echo "Redis Server Started"
