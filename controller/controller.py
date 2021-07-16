from threading import Thread
from .command_queue import command_queue
from .timer import timer
from ..utils import const_command
from ..route_default.rt_default import rt_default
from ..topo.swslot import swslot
from ..topo.ctrlslot import ctrlslot
from ..topo.dbload import dbload
import os


def load_command():
    # 命令常量定义
    # cli命令
    const_command.cli_run_topo = 0
    const_command.cli_run_iperf = 1
    const_command.cli_stop_iperf = 2
    const_command.cli_sw_shutdown = 3
    const_command.cli_sw_recover = 4
    const_command.cli_ctrl_shutdown = 5
    const_command.cli_ctrl_recover = 6
    const_command.cli_db_shutdown = 7
    const_command.cli_db_recover = 8
    const_command.cli_stop_all = 9
    # timer定时器切换命令
    const_command.timer_diff = 10
    const_command.timer_rt_diff = 11

class controller:
    def __init__(self, filePath:str) -> None:
        # 加载卫星交换机拓扑
        self.dslot = swslot(filePath + '/config')
        # 加载openmul控制器
        self.cslot = ctrlslot(filePath + '/config')
        # 加载分布式数据库
        self.dbdata = dbload(filePath + '/config/rt_ctrl2db/db_deploy')
        # 加载时间片序列
        self.topotimer = timer(filePath + '/config/timeslot/timefile', 0, 10)
        self.rttimer = timer(filePath + '/config/timeslot/timefile', 20, 11)
        # 初始化默认流表
        self.rt_default = rt_default(filePath + "/config")
        # self.rt_ctrl2db = rt_ctrl2db(filePath + '/config/rt_ctrl2db')
        # self.rt_ctrl2sw = rt_ctrl2sw(filePath + '/config/rt_ctrl2sw')
        # self.rt_db2db = rt_db2db(filePath + '/config/rt_db2db')
        # self.rt_sw2sw = rt_sw2sw(filePath + '/config/rt_sw2sw')
        # 加载指令
        load_command()
        self.status = False
        self.start()

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = command_queue.read_queue_wait()
            if self.status == False: return

            if(command[0] == const_command.cli_run_topo):
                # rt_ctrl2db.load_rt_ctrl2db(self.rt_ctrl2db.rt_ctrl2db_slot[0], self.rt_ctrl2db.rt_db2ctrl_slot[0])
                # rt_ctrl2sw.load_rt_ctrl2sw(self.rt_ctrl2sw.rt_ctrl2sw_slot[0], self.rt_ctrl2sw.rt_sw2ctrl_slot[0])
                # rt_db2db.load_rt_db2db(self.rt_db2db.rt_db2db_slot[0])
                # rt_sw2sw.load_rt_sw2sw(self.rt_sw2sw.rt_sw2sw_slot0)
                # self.rt_default.load_rt_default()
                # 设置卫星交换机连接控制器
                datactrl = self.cslot.ctrl_slot[0]
                for ctrl in datactrl:
                    for sw in datactrl[ctrl]:
                        os.system("sudo docker exec -it s{} ovs-vsctl set-controller \
                            s{} tcp:192.168.67.{}:6653".format(sw, sw+1, ctrl))
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
                slot_no = command[1]   # 获取切换的时间片
                print("第{}个时间片切换，topo的链路修改".format(slot_no))
                swslot.sw_links_change(self.dslot, slot_no)
                # 设置卫星交换机连接控制器
                cslot_b = self.cslot.ctrl_slot[slot_no]
                cslot_n = self.cslot.ctrl_slot[slot_no + 1]
                for ctrl in cslot_n:
                    for sw in cslot_n[ctrl]:
                        if sw not in cslot_b[ctrl]:
                            os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}:6653".format(sw, sw, ctrl))
                print("第{}个时间片切换，删除不需要的控制器\n".format(slot_no))
                Thread(target=ctrlslot.ctrl_change_del, args=(self.cslot, slot_no)).start()

            elif(command[0] ==  const_command.timer_rt_diff):
                slot_no = command[1]   # 获取切换的时间片
                print("第{}个时间片切换默认路由\n".format(slot_no))
                rt_default.change_rt_default(self.rt_default.sw_num, slot_no)
                print("第{}个时间片切换，添加下一个时间片的控制器\n".format(slot_no))
                Thread(target=ctrlslot.ctrl_change_add, args=(self.cslot, slot_no)).start()
                
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
