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


def sw_connect_ctrl_init(sw, ip_master, ip_standby):
    os.system("(sudo docker exec s{} /home/sw_slot_change {} {} {} > /dev/null &) ".format(sw, sw, ip_master+1, ip_standby+1))

def sw_connect_ctrl(sw, ip_master, ip_standby):
    # 卫星交换机连接控制器
    # os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}:6653 -- set bridge s{} other_config:enable-flush=false"\
    #     .format(sw, sw, ctrl+1, sw))
    # print("slot:{}, sw:{}".format(slot_no, sw))
    # os.system("sudo docker exec -it s{sw} chmod +x /home/sw{sw}_standby_slot{slot_no}.sh;sudo docker exec -it s{sw} /bin/bash /home/sw{sw}_standby_slot{slot_no}.sh"\
    #     .format(sw=sw, slot_no=slot_no))
    os.system("sudo docker exec -it s{} /bin/bash -c \"echo {} {} > /dev/udp/127.0.0.1/12000\"".format(sw, ip_master+1, ip_standby+1))

def run_shell(file):
    # 运行shell文件
    # print("run {}".format(file))
    os.system("sudo chmod +x {file}; sudo {file}".format(file=file))

def ctrl_get_slot_change(slot_no, ctrl_no):
    os.system("sudo docker exec -it c{} /bin/bash -c \"echo {} > /dev/udp/192.168.67.{}/12000\"".format(ctrl_no, slot_no, ctrl_no+1))

def db_get_slot_change(slot_no, db_no):
    os.system("sudo docker exec -it db{} /bin/bash -c \"echo {} > /dev/udp/192.168.68.{}/12000\"".format(db_no, slot_no, db_no+1))


if __name__ == "__main__":
    #获取当前文件路径，读取配置文件需要
    filePath = os.path.dirname(__file__)
    
    os.system("sudo ovs-vsctl show > /dev/null")

    ctrl = controller(filePath)
    rt = rt_default(filePath + '/config')

    with ThreadPoolExecutor(max_workers=66) as pool:
        all_task = []
        for sw in range(ctrl.dslot.sw_num): 
            all_task.append(pool.submit(sw_connect_ctrl, sw, ctrl.cslot.sw2ctrl[0][sw], ctrl.cslot.sw2ctrl_standby[0][sw]))
        wait(all_task, return_when=ALL_COMPLETED)
        for ctrl_no in ctrl.cslot.ctrl_slot[0]:
            all_task.append(pool.submit(ctrl_get_slot_change, 0, ctrl_no))
        wait(all_task, return_when=ALL_COMPLETED)
    time.sleep(15)
    with ThreadPoolExecutor(max_workers=10) as pool:
        all_task = []
        for db_no in ctrl.dbdata.db_data:
            all_task.append(pool.submit(db_get_slot_change, 0, db_no))
        wait(all_task, return_when=ALL_COMPLETED)
    
    # slot_no = 0   # 获取切换的时间片
    for slot_no in range(44):
        print("第{}个时间片切换默认路由 {}".format(slot_no, time.time()))
        rt_default.change_rt_default(len(ctrl.dslot.data_slot[0]), slot_no)

        print("第{}个时间片切换，添加下一个时间片的控制器 {}".format(slot_no, time.time()))
        ctrlslot.ctrl_change_add(ctrl.cslot, slot_no)

        time.sleep(15)

        slot_next = (slot_no+1)%ctrl.cslot.slot_num
        print("第{}个时间片切换 {}".format(slot_no, time.time()))
        # Thread(target=controller.slot_change, args=(ctrl, slot_next,)).start()
        ctrl.slot_change(slot_next)

        print("topo的链路修改 {}\n\n".format(slot_no, time.time()))
        swslot.sw_links_change(ctrl.dslot, slot_no)

        print("第{}个时间片切换，删除不需要的控制器和路由 {}".format(slot_no, time.time()))
        ctrlslot.ctrl_change_del(ctrl.cslot, slot_no)
        print("第{}个时间片切换，删除不需要的控制器和路由 {}".format(slot_no, time.time()))
        rt_default.del_rt_default_ctrl(len(ctrl.dslot.data_slot[0]), slot_no)

        time.sleep(10)
        # for sw in range(66):
        #     os.system("sudo docker exec -it s{} ovs-vsctl show >> slot{}.txt".format(sw, slot_no))

    print("end")