from threading import Thread
from .command_queue import command_queue
from .timer import timer
from ..utils import const_command
from ..topo.flowbuilder import flowbuilder
from ..topo.topobuilder import topobuilder
from ..topo.topobuilder import sw_dr
from ..config.rt_ctrl2db import rt_ctrl2db
from ..config.rt_ctrl2sw import rt_ctrl2sw
from ..config.rt_db2db import rt_db2db
from ..config.rt_sw2sw import rt_sw2sw
from ..config.swsolt import swsolt
from ..config.ctrlslot import ctrlslot
from ..config.dbload import dbload


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
        self.dslot = swsolt(filePath + '/config/timeslot')
        # 加载openmul控制器
        self.cslot = ctrlslot(filePath + '/config/ctrl_deploy')
        # 加载分布式数据库
        self.dbdata = dbload(filePath + '/config/rt_ctrl2db/db_deploy')
        # 加载时间片序列
        self.ctimer = timer(filePath + '/config/timeslot/timefile')
        # 初始化拓扑
        topobuilder.load_slot(self.dslot.data_slot[0])
        topobuilder.load_ctrl(self.cslot.ctrl_slot[0])
        topobuilder.load_db(self.dbdata.db_data)
        # 初始化默认流表
        self.rt_ctrl2db = rt_ctrl2db(filePath + '/config/rt_ctrl2db')
        self.rt_ctrl2sw = rt_ctrl2sw(filePath + '/config/rt_ctrl2sw')
        self.rt_db2db = rt_db2db(filePath + '/config/rt_db2db')
        self.rt_sw2sw = rt_sw2sw(filePath + '/config/rt_sw2sw')
        # 加载指令
        load_command()

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = command_queue.read_queue_wait()

            if(command[0] == const_command.cli_run_topo):
                rt_ctrl2db.load_rt_ctrl2db(self.rt_ctrl2db.rt_ctrl2db_slot[0], self.rt_ctrl2db.rt_db2ctrl_slot[0])
                rt_ctrl2sw.load_rt_ctrl2sw(self.rt_ctrl2sw.rt_ctrl2sw_slot[0], self.rt_ctrl2sw.rt_sw2ctrl_slot[0])
                rt_db2db.load_rt_db2db(self.rt_db2db.rt_db2db_slot[0])
                rt_sw2sw.load_rt_sw2sw(self.rt_sw2sw.rt_sw2sw_slot0)
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
                index = self.ctimer.index   # 获取当前的时间片
                topobuilder.change_slot_ctrl(self.cslot.ctrl_slot[index], self.cslot.ctrl_slot[index + 1])  # 切换控制器
                # 先是删除下个时间片没有的默认路由
                rt_ctrl2db.delete_rt_ctrl2db(self.rt_ctrl2db.rt_ctrl2db_diff[index], self.rt_ctrl2db.rt_db2ctrl_diff[index])
                rt_ctrl2sw.delete_rt_ctrl2sw(self.rt_ctrl2sw.rt_ctrl2sw_diff[index], self.rt_ctrl2sw.rt_sw2ctrl_diff[index])
                rt_db2db.delete_rt_db2db(self.rt_db2db.rt_db2db_diff[index])
                rt_sw2sw.delete_rt_sw2sw(self.rt_sw2sw.rt_sw2sw_diff[index])
                # 卫星交换机的连接切换
                topobuilder.change_slot_sw(self.dslot.data_slot[index])
                # 添加新的上个时间片没有的路由
                rt_ctrl2db.add_rt_ctrl2db(self.rt_ctrl2db.rt_ctrl2db_diff[index], self.rt_ctrl2db.rt_db2ctrl_diff[index])
                rt_ctrl2sw.add_rt_ctrl2sw(self.rt_ctrl2sw.rt_ctrl2sw_diff[index], self.rt_ctrl2sw.rt_sw2ctrl_diff[index])
                rt_db2db.add_rt_db2db(self.rt_db2db.rt_db2db_diff[index])
                rt_sw2sw.add_rt_sw2sw(self.rt_sw2sw.rt_sw2sw_diff[index])         
    
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