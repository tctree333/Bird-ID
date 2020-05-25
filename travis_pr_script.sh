echo "Starting Local Redis Server"
redis-server &
export SCIOLY_ID_BOT_LOCAL_REDIS="true"
export SCIOLY_ID_BOT_USE_SENTRY="false"
echo "Redis Server Started"
