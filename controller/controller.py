from threading import Thread
from .command_queue import command_queue
from .timer import timer
from ..utils import const_command
from ..topo.flowbuilder import flowbuilder
from ..topo.topobuilder import topobuilder
from ..topo.topobuilder import sw_dr
from ..config.rt_default import rt_default
from ..config.swsolt import swsolt
from ..config.ctrlslot import ctrlslot
from ..config.dbload import dbload
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

class controller:
    def __init__(self, filePath:str) -> None:
        # 加载卫星交换机拓扑
        self.dslot = swsolt(filePath + '/config')
        # 加载openmul控制器
        self.cslot = ctrlslot(filePath + '/config')
        # 加载分布式数据库
        self.dbdata = dbload(filePath + '/config/rt_ctrl2db/db_deploy')
        # 加载时间片序列
        self.ctimer = timer(filePath + '/config/timeslot/timefile')
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
                self.ctimer.start()

            elif(command[0] == const_command.cli_run_iperf):
                flowbuilder.random_iperf_period(len(topobuilder.sw_set))

            elif(command[0] == const_command.cli_stop_iperf):
                flowbuilder.stop()

            elif(command[0] == const_command.cli_sw_shutdown):
                sw_dr.disable_sw(command[1])

            elif(command[0] == const_command.cli_sw_recover):
                sw_dr.enable_sw[command[1]]
                
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

            elif(command[0] ==  const_command.timer_diff):
                index = command[1]   # 获取切换的时间片
                cslot_b = self.cslot.ctrl_slot[index]
                cslot_n = self.cslot.ctrl_slot[index + 1]
                # topobuilder.change_slot_ctrl(cslot_b, cslot_n)  # 切换控制器
                # 先是删除下个时间片没有的默认路由
                self.rt_default.del_rt_default(index)
                # rt_ctrl2db.delete_rt_ctrl2db(self.rt_ctrl2db.rt_ctrl2db_diff[index], self.rt_ctrl2db.rt_db2ctrl_diff[index])
                # rt_ctrl2sw.delete_rt_ctrl2sw(self.rt_ctrl2sw.rt_ctrl2sw_diff[index], self.rt_ctrl2sw.rt_sw2ctrl_diff[index])
                # rt_db2db.delete_rt_db2db(self.rt_db2db.rt_db2db_diff[index])
                # rt_sw2sw.delete_rt_sw2sw(self.rt_sw2sw.rt_sw2sw_diff[index])
                # 卫星交换机的连接切换
                # topobuilder.change_slot_sw(self.dslot.data_slot[index])
                self.dslot.sw_links_change(index)
                # 添加新的上个时间片没有的路由
                self.rt_default.add_rt_default(self.rt_default.sw_flow_diff_add)
                # rt_ctrl2db.add_rt_ctrl2db(self.rt_ctrl2db.rt_ctrl2db_diff[index], self.rt_ctrl2db.rt_db2ctrl_diff[index])
                # rt_ctrl2sw.add_rt_ctrl2sw(self.rt_ctrl2sw.rt_ctrl2sw_diff[index], self.rt_ctrl2sw.rt_sw2ctrl_diff[index])
                # rt_db2db.add_rt_db2db(self.rt_db2db.rt_db2db_diff[index])
                # rt_sw2sw.add_rt_sw2sw(self.rt_sw2sw.rt_sw2sw_diff[index])  
                # print("!")
                # 设置卫星交换机连接控制器
                for ctrl in cslot_n:
                    if ctrl not in topobuilder.ctrl_set:
                        topobuilder.ctrl_set.add(ctrl)
                        os.system("sudo docker start c{} > /dev/null".format(ctrl))  # 启动docker
                        topobuilder.load_ctrl_link(ctrl)
                    for sw in cslot_n[ctrl]:
                        if sw not in cslot_b[ctrl] and sw not in sw_dr.sw_disable_set:
                            os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}:6653".format(sw, sw, ctrl))
    
    def start(self):
        # 开启线程
        if self.status:
            return False
        else:
            Thread(target=self.__do_start).start()
            self.status = True
        return True

    def stop(self):
        # 关闭线程
        self.started = False
        self.ctimer.stop()
        topobuilder.del_slot()