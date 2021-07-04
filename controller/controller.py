import os
from threading import Thread
from typing import Dict
from controller.command_queue import command_queue
from utils.const_command import const_command
from config.swsolt import swsolt
from config.timer import timer
from topo.topobuilder import topobulider, sw_dr
from topo.flowbuilder import flowbuilder
from config.ctrlslot import ctrlslot


class controller:
    def __init__(self, filePath:str) -> None:
        # 加载卫星交换机拓扑
        self.dslot = swsolt(filePath + '/config/timeslot')
        # 加载openmul控制器
        self.cslot = ctrlslot(filePath + '/config/ctrl_deploy')
        # 加载时间片序列
        self.ctimer = timer(filePath + '/config/timeslot/timefile')

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = command_queue.read_queue_wait()

            if(command[0] == const_command.cli_run_topo):
                topobulider.load_slot(self.dslot.data_slot[0])
                topobulider.load_ctrl(self.cslot.ctrl_slot[0])
                self.ctimer.start()

            elif(command[0] == const_command.cli_run_iperf):
                flowbuilder.random_iperf_period(len(topobulider.sw_set))

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
                topobulider.change_slot_sw(self.dslot.data_slot[self.ctimer.index])
                topobulider.change_slot_ctrl(self.cslot.ctrl_slot[self.ctimer.index], self.cslot.ctrl_slot[self.ctimer.index + 1])                    
    
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