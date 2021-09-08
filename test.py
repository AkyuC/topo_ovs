import os,sys
from controller.controller import controller
from threading import Thread
from utils import const_command
from route_default.rt_default import rt_default
from topo.swslot import swslot
from topo.ctrlslot import ctrlslot
from topo.dbload import dbload
import os
import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import multiprocessing


def sw_connect_ctrl(sw, slot_no):
    # 卫星交换机连接控制器
    # os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}:6653 -- set bridge s{} other_config:enable-flush=false"\
    #     .format(sw, sw, ctrl+1, sw))
    os.system("sudo docker exec -it s{sw} chmod +x /home/sw{sw}_standby_slot{slot_no}.sh;sudo docker exec -it s{sw} /bin/bash /home/sw{sw}_standby_slot{slot_no}.sh"\
        .format(sw=sw, slot_no=slot_no))

def run_shell(file):
    # 运行shell文件
    os.system("sudo chmod +x {file}; sudo {file}".format(file=file))


if __name__ == "__main__":
    #获取当前文件路径，读取配置文件需要
    filePath = os.path.dirname(__file__)
    
    os.system("sudo ovs-vsctl show > /dev/null")

    ctrl = controller(filePath)
    rt = rt_default(filePath + '/config')

    for sw in range(66):
        ctrl.processespool.apply_async(sw_connect_ctrl, (sw,0, ))
    time.sleep(10)
    for sw in range(66):
        os.system("sudo docker exec -it s{} ovs-vsctl show >> a.txt".format(sw))

    # ctrl.processespool.close()
    # ctrl.processespool.join()
    time.sleep(10)
    
    slot_no = 0   # 获取切换的时间片
    print("第{}个时间片切换默认路由\n".format(slot_no))
    rt_default.change_rt_default(len(ctrl.dslot.data_slot[0]), slot_no)

    print("第{}个时间片切换，添加下一个时间片的控制器\n".format(slot_no))
    ctrlslot.ctrl_change_add(ctrl.cslot, slot_no)
    
    time.sleep(20)

    ctrl.processespool.apply_async(run_shell, ("{}/config/ctrl_shell/ctrl_restart_slot{}.sh > /dev/null"\
        .format(ctrl.filePath,slot_no),))

    print("第{}个时间片切换，topo的链路修改".format(slot_no))
    swslot.sw_links_change(ctrl.dslot, slot_no)

    print("第{}个时间片切换，卫星交换机连接对于的控制器".format(slot_no))
    for sw in range(len(ctrl.dslot.data_slot[0])):
        ctrl.processespool.apply_async(sw_connect_ctrl, (sw,slot_no+1, ))

    print("第{}个时间片切换，删除不需要的控制器和相关的路由\n\n\n".format(slot_no))
    ctrlslot.ctrl_change_del(ctrl.cslot, slot_no)
    rt_default.del_rt_default_ctrl(len(ctrl.dslot.data_slot[0]), slot_no)
    ctrl.processespool.close()
    ctrl.processespool.join()

    time.sleep(10)
    for sw in range(66):
        os.system("sudo docker exec -it s{} ovs-vsctl show >> b.txt".format(sw))

    print("end")