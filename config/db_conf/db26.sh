#!/bin/sh
#redis
REDISPORT=6379
#服务端所处位置
REDIS_EXEC=/usr/bin/redis-server
#客户端位置
CLIREDIS_EXEC=/usr/bin/redis-cli
#redis的PID文件位置，需要修改
REDIS_PIDFILE=/var/run/redis-server.pid
#redis的配置文件位置，需将${REDIS_REDISPORT}修改为文件名
REDIS_CONF="/home/redis26.conf"

REDIS_IP="192.168.68.27"

#dynomite
#
DYNOMITE_EXEC=/usr/sbin/dynomite
#
DYNOMITE_CONF="/home/dyno_26.yml"
#
DYNOMITE_LOG="/home/dynomite.log"

start_redis(){
    if [ -f $REDIS_PIDFILE ]
    then
            echo "$REDIS_PIDFILE exists, process is already running or crashed"
    else
            $REDIS_EXEC $REDIS_CONF 
    fi
}

stop_redis(){
if [ ! -f $PIDFILE ]
    then
            echo "$PIDFILE does not exist, process is not running"
    else
            PID=$(cat $REDIS_PIDFILE)
            $CLIREDIS_EXEC -h $REDIS_IP -p $REDISPORT shutdown
            while [ -x /proc/${PID} ]
            do
                sleep 1
            done
    fi
    killall -9 redis-cli 
}

stop_dynomite(){
    killall -9 dynomite 
}

start_dynomite(){
    $DYNOMITE_EXEC -c $DYNOMITE_CONF -d --output=$DYNOMITE_LOG
}

restart_redis(){
    if [ ! -f $REDIS_PIDFILE ]
    then
            $REDIS_EXEC $REDIS_CONF 
    else
            PID=$(cat $REDIS_PIDFILE)
            $CLIREDIS_EXEC -h $REDIS_IP -p $REDIS_REDISPORT shutdown
            while [ -x /proc/${PID} ]
            do
                sleep 1
            done
            $REDIS_EXEC $REDIS_CONF 
    fi
}
 
case "$1" in
    start)
        start_redis
        start_dynomite
        ;;
    stop)
        stop_dynomite
        stop_redis
        ;;
    restart)
        stop_dynomite
        restart_redis
        start_dynomite
        ;;
    *) echo "unknown command"
        ;;
esac
