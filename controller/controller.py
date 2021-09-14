from threading import Thread
from .timer import timer
from utils import const_command
from route_default.rt_default import rt_default
from topo.swslot import swslot
from topo.ctrlslot import ctrlslot
from topo.dbload import dbload
import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from socket import *
from time import sleep

class UdpServer:
    def __init__(self):
        #define the type of socket is IPv4 and Udp
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(('127.0.0.1', 12001))
    
    def recv_msg(self):
        msg, addr = self.serverSocket.recvfrom(2048)
        return msg.decode('utf-8')

def load_command():
    # 命令常量定义
    # cli命令
    const_command.cli_run_topo = 0
    const_command.cli_run_iperf = 1
    const_command.cli_stop_iperf = 2
    const_command.cli_ctrl_shutdown = 3
    const_command.cli_ctrl_recover = 4
    const_command.cli_db_shutdown = 5
    const_command.cli_db_recover = 6
    const_command.cli_stop_all = 7
    # timer定时器切换命令
    const_command.timer_diff = 8
    const_command.timer_rt_diff = 9

def sw_connect_ctrl_init(sw, ip_master, ip_standby):
    os.system("(sudo docker exec s{} /home/sw_slot_change {} {} {} > /dev/null &) ".format(sw, sw, ip_master+1, ip_standby+1))

def sw_connect_ctrl(sw, ip_master, ip_standby):
    # 卫星交换机连接控制器
    # os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}:6653 -- set bridge s{} other_config:enable-flush=false"\
    #     .format(sw, sw, ctrl+1, sw))
    # print("slot:{}, sw:{}".format(slot_no, sw))
    # os.system("sudo docker exec -it s{sw} chmod +x /home/sw{sw}_standby_slot{slot_no}.sh;sudo docker exec -it s{sw} /bin/bash /home/sw{sw}_standby_slot{slot_no}.sh"\
    #     .format(sw=sw, slot_no=slot_no))
    os.system("sudo docker exec -it s{} /bin/bash -c \"echo {} {} > /dev/udp/localhost/12000\"".format(sw, ip_master+1, ip_standby+1))

def run_shell(file):
    # 运行shell文件
    # print("run {}".format(file))
    os.system("sudo chmod +x {file}; sudo {file}".format(file=file))

def ctrl_get_slot_change(slot_no, ctrl_list):
    for ctrl_no in ctrl_list:
        os.system("sudo docker exec -it c{} /bin/bash -c \"echo {} > /dev/udp/127.0.0.1/12000\"".format(ctrl_no, slot_no))

class controller:
    def __init__(self, filePath:str) -> None:
        self.filePath = filePath
        # 加载卫星交换机拓扑
        self.dslot = swslot(filePath + '/config')
        # 加载openmul控制器
        self.cslot = ctrlslot(filePath + '/config')
        # 加载分布式数据库
        self.dbdata = dbload(filePath + '/config')
        # 加载时间片序列
        self.topotimer = timer(filePath + '/config/timeslot/timefile', 0, 8)
        self.rttimer = timer(filePath + '/config/timeslot/timefile', 20, 9)
        # 加载指令
        load_command()
        self.status = False
        self.socket = UdpServer()
        self.start()

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = self.socket.recv_msg().split()
            command = list(map(int, command))
            if self.status == False: return

            if(command[0] == const_command.cli_run_topo):
                print("开始运行topo!")
                # # 设置卫星交换机连接控制器
                with ThreadPoolExecutor(max_workers=45) as pool:
                    all_task = []
                    for sw in range(self.dslot.sw_num):
                        # all_task.append(pool.submit(sw_connect_ctrl, sw, 0)) 
                        all_task.append(pool.submit(sw_connect_ctrl_init, sw, self.cslot.sw2ctrl[0][sw], self.cslot.sw2ctrl_standby[0][sw]))
                    wait(all_task, return_when=ALL_COMPLETED)
                print("启动定时器!")
                self.topotimer.start()
                self.rttimer.start()

            elif(command[0] == const_command.cli_run_iperf):
                pass
            elif(command[0] == const_command.cli_stop_iperf):
                pass
            elif(command[0] == const_command.cli_ctrl_shutdown):
                pass
            elif(command[0] == const_command.cli_ctrl_recover):
                pass
            elif(command[0] == const_command.cli_db_shutdown):
                pass
            elif(command[0] == const_command.cli_db_recover):
                pass
            elif(command[0] == const_command.cli_stop_all):
                self.stop()
                return

            elif(command[0] ==  const_command.timer_diff):
                slot_no = command[1]   # 获取切换的时间片序号

                print("第{}个时间片切换，topo的链路修改".format(slot_no))
                # Thread(target=run_shell, args=("{}/config/ctrl_shell/ctrl_restart_slot{}.sh > /dev/null"\
                #     .format(self.filePath,slot_no),)).start()
                Thread(target=ctrl_get_slot_change, args=(slot_no, self.cslot.ctrl_slot_stay[slot_no],)).start()
                swslot.sw_links_change(self.dslot, slot_no)

                print("第{}个时间片切换，卫星交换机连接对于的控制器".format(slot_no))
                slot_next = (slot_no+1)%self.cslot.slot_num
                with ThreadPoolExecutor(max_workers=45) as pool:
                    all_task = []
                    for sw in range(self.dslot.sw_num):
                        # all_task.append(pool.submit(sw_connect_ctrl, sw, slot_no+1)) 
                        all_task.append(pool.submit(sw_connect_ctrl, sw, self.cslot.sw2ctrl[slot_next][sw], self.cslot.sw2ctrl_standby[slot_next][sw]))
                    wait(all_task, return_when=ALL_COMPLETED)

                print("第{}个时间片切换，删除不需要的控制器和路由\n".format(slot_no))
                ctrlslot.ctrl_change_del(self.cslot, slot_no)
                rt_default.del_rt_default_ctrl(len(self.dslot.data_slot[0]), slot_no)


            elif(command[0] ==  const_command.timer_rt_diff):
                slot_no = command[1]   # 获取切换的时间片
                print("第{}个时间片切换默认路由".format(slot_no))
                rt_default.change_rt_default(len(self.dslot.data_slot[0]), slot_no)

                print("第{}个时间片切换，添加下一个时间片的控制器".format(slot_no))
                ctrlslot.ctrl_change_add(self.cslot, slot_no)


    def start(self):
        # 开启线程
        if self.status:
            return False
        else:
            self.status = True
            Thread(target=self.__do_start).start()
        return True

    def stop(self):
        # 关闭线程
        self.started = False
        self.topotimer.stop()
        self.rttimer.stop()
        os.system("sudo docker stop $(sudo docker ps -a -q)")
        os.system("sudo docker rm $(sudo docker ps -a -q)")
