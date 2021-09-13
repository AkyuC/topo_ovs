#ifndef __SW_EXEC_H__
#define __SW_EXEC_H__

#define uint8_t unsigned char
#define UDP_BUFF_LEN 512    //套接字缓存大小
#define SLOT_NUM 44 // 时间片个数
#define SERVER_PORT 12000   //监听端口
#define TIME_INTERVAL 10 //时间间隔10s
void* pkt_listen(void *arg);

#endif