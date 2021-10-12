#include <stdlib.h>
#include <stdio.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <pthread.h>
#include <string.h>
#include "sw_slot_change.h"

int server_fd = -1; // 监听的套接字
int sw_no = -1; // 卫星交换机的序号
int ip_master = 0;  // 主控制器的ip
int ip_standby = 0; // 备控制器的ip
// int ctrl[2][SLOT_NUM] = {0}; //主备控制器，第一行为主，第二行为备
pthread_mutex_t mutex; // 线程锁

int listen_init(void)
{
    // 初始化监听套接字
    int ret;
    struct sockaddr_in ser_addr;
    char ip[20] = {'\0'};
    sprintf(ip, "192.168.66.%d", sw_no+1);

    server_fd = socket(AF_INET, SOCK_DGRAM, 0); //AF_INET:IPV4;SOCK_DGRAM:UDP
    if(server_fd < 0)
    {
        printf("create socket fail!\n");
        return -1;
    }

    memset(&ser_addr, 0, sizeof(ser_addr));
    ser_addr.sin_family = AF_INET;
    ser_addr.sin_addr.s_addr = inet_addr(ip); //IP地址，需要进行网络序转换，INADDR_ANY：本地地址
    ser_addr.sin_port = htons(SERVER_PORT);  //端口号，需要网络序转换

    ret = bind(server_fd, (struct sockaddr*)&ser_addr, sizeof(ser_addr));
    if(ret < 0)
    {
        printf("socket bind fail!\n");
        return -1;
    }
    return 0;
}

void* ctrl_connect(void* arg)
{
    // 测试到控制器的连通性，连接控制器
    char command[UDP_BUFF_LEN] = {'\0'};
    int tmp = 0;

	while(1)
	{
        if(ip_master && ip_standby)
        {
            sprintf(command, "ping -c2 -i0.1 -W1 192.168.67.%d > /dev/null &", ip_master);
            if(system(command) != 0)
            {
                if(pthread_mutex_trylock(&mutex) != 0)
                {
                    sleep(1);
                    pthread_testcancel();
                    continue;
                }
                tmp = ip_standby;
                ip_standby = ip_master;
                ip_master = tmp;
                pthread_mutex_unlock(&mutex);
                sprintf(command, "ovs-vsctl set-controller s%d tcp:192.168.67.%d:6653 -- set controller s%d connection-mode=out-of-band", sw_no,ip_master,sw_no);
                system(command);
            }
        }
        sleep(5);
        pthread_testcancel();
	}
}

int main(int argc,char *argv[])
{
    // 需要传入参数 1交换机编号 2主控制器编号 3备控制器编号
    // 编译命令 /usr/bin/gcc-9 -g ./sw_slot_change.c ./sw_slot_change.h -o sw_slot_change -lpthread
    uint8_t buf[UDP_BUFF_LEN] = {'\0'};
    int i, tmp1, tmp2;
    struct sockaddr_in *clent_addr;
    socklen_t len = sizeof(struct sockaddr_in);
    pthread_t pid;
    char command[UDP_BUFF_LEN] = {'\0'};
    
    if(argc <= 0)return -1;
    // 初始化
    sw_no = atoi(argv[1]);
    if(listen_init() != 0)
    {
        printf("套接字初始化失败\n"); 
        return -1;
    }
    if(pthread_mutex_init(&mutex, NULL) != 0)
    {
        printf("线程锁初始化失败\n");
        close(server_fd);
        return -1;
    }

    recvfrom(server_fd, buf, UDP_BUFF_LEN, 0, (struct sockaddr*)clent_addr, &len);
    // 收到的信息为主控制器编号 备控制器编号
    i = 0;
    tmp1 = 0;
    tmp2 = 0;
    while (1)
    {
        if(buf[i] != ' ' && buf[i] != '\0' && buf[i] != '\n')
        {
            tmp1 = tmp1*10 + buf[i] - '0';
            i++;
        }else
        {
            i++;
            break;
        }
    }
    while (1)
    {
        if(buf[i] != ' ' && buf[i] != '\0' && buf[i] != '\n')
        {
            tmp2 = tmp2*10 + buf[i] - '0';
            i++;
        }else
        {
            break;
        }
    }
    pthread_mutex_lock(&mutex);
    ip_master = tmp1;
    ip_standby = tmp2;
    pthread_mutex_unlock(&mutex);

    sprintf(command, "ovs-vsctl set-controller s%d tcp:192.168.67.%d:6653 -- set controller s%d connection-mode=out-of-band", sw_no,ip_master,sw_no);
    system(command);

    // 创建控制器设置线程
    if(pthread_create(&pid, NULL, ctrl_connect, NULL) != 0)
    {
        printf("创建线程失败\n");
        pthread_mutex_destroy(&mutex);
        pthread_cancel(pid);
	    pthread_join(pid, NULL);
        close(server_fd);
        return -1;
    }

	while(1)
	{
        recvfrom(server_fd, buf, UDP_BUFF_LEN, 0, (struct sockaddr*)clent_addr, &len);
        // 收到的信息为主控制器编号 备控制器编号
        i = 0;
        tmp1 = 0;
        tmp2 = 0;
        while (1)
        {
            if(buf[i] != ' ' && buf[i] != '\0' && buf[i] != '\n')
            {
                tmp1 = tmp1*10 + buf[i] - '0';
                i++;
            }else
            {
                i++;
                break;
            }
        }
        while (1)
        {
            if(buf[i] != ' ' && buf[i] != '\0' && buf[i] != '\n')
            {
                tmp2 = tmp2*10 + buf[i] - '0';
                i++;
            }else
            {
                break;
            }
        }
        pthread_mutex_lock(&mutex);
        ip_master = tmp1;
        ip_standby = tmp2;
        pthread_mutex_unlock(&mutex);

        sprintf(command, "ovs-vsctl set-controller s%d tcp:192.168.67.%d:6653 -- set controller s%d connection-mode=out-of-band", sw_no,ip_master,sw_no);
        system(command);

        sprintf(command, "ping -c2 -i0.1 -W1 192.168.67.%d > /dev/null &", ip_master);
        if(system(command) != 0)
        {
            pthread_mutex_lock(&mutex);
            tmp1 = ip_standby;
            ip_standby = ip_master;
            ip_master = tmp1;
            pthread_mutex_unlock(&mutex);
            sprintf(command, "ovs-vsctl set-controller s%d tcp:192.168.67.%d:6653 -- set bridge s%d other_config:disable-in-band=false;ovs-vsctl set controller s%d connection-mode=out-of-band", sw_no,ip_master,sw_no,sw_no);
            system(command);
        }
        memset(buf, 0, 20);
	}

    return 0;
}