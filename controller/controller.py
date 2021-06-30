import os
from threading import Thread
from typing import Dict
from controller.command_queue import command_queue
from utils.const_command import const_command
from config.datasolt import datasolt
from config.timer import timer
from topo.topobuilder import topobulider
from namespace.nsbuilder import nsbuilder


class controller:
    def __init__(self, filePath:str) -> None:
        # 获取第一个时间片和时间片之间的不同连接关系
        self.dslot = datasolt()
        self.dslot.start(filePath)
        # 加载时间片序列
        self.ctimer = timer()
        self.ctimer.load_time_seq(filePath + '/timeslot/timefile')

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = command_queue.read_queue_wait()

            if(command[0] == const_command.cli_run_topo):
                topobulider.load_slot(self.dslot.slot0)
                self.ctimer.start()

            elif(command[0] == const_command.cli_run_ping):
                nsbuilder.random_ping_period()

            elif(command[0] == const_command.cli_stop_ping):
                nsbuilder.stop()

            elif(command[0] == const_command.cli_sw_reload):
                pass
            elif(command[0] == const_command.cli_ctrl_reload):
                pass
            elif(command[0] == const_command.cli_db_reload):
                pass

            elif(command[0] == const_command.cli_stop_all):
                self.stop()

            elif(command[0] ==  const_command.timer_diff):
                topobulider.change_slot_sw(self.dslot.data_slot[self.ctimer.index])
    
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
        topobulider.del_slot()