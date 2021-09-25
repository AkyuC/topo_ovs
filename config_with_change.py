import os
import time
from topo.swslot import swslot
from route_default.rt_default import rt_default
from topo.ctrlslot import ctrlslot
from topo.dbload import dbload
from controller.controller import sw_connect_ctrl
from threading import Thread

def load_db(filePath):
    # 初始化数据库
    dbdata = dbload(filePath + '/config')
    print("--将分布式数据库放入topo")
    dbdata.load_db()


if __name__ == "__main__":
    filePath = os.path.dirname(__file__)

    if not os.path.exists(filePath + "/config/sw_shell"):
        os.makedirs(filePath + "/config/sw_shell")
    if not os.path.exists(filePath + "/config/ctrl_shell"):
        os.makedirs(filePath + "/config/ctrl_shell")
    if not os.path.exists(filePath + "/config/rt_shell"):
        os.makedirs(filePath + "/config/rt_shell")
    # 初始化拓扑
    # 初始化卫星交换机和卫星交换机之间的连接
    sws = swslot(filePath + "/config")    
    os.system("sudo ovs-vsctl show > /dev/null")
    print("--生成链路连接sh脚本，并且复制到对应的docker当中")
    sws.config2sh()
    print("--启动卫星交换机对应的docker和ovs，并且加载第一个时间片的拓扑")
    sws.sw_links_init()
    
    # 初始化第一个时间片的默认路由
    rt = rt_default(filePath + '/config')
    os.system("sudo ovs-vsctl show > /dev/null")
    print("--生成默认路由sh脚本，包括第一个时间片的默认路由和时间片切换需要增删的流表项，并且复制到对应的docker")
    rt.config2sh()
    print("--加载第一个时间片的默认流表")
    rt.load_rt_default()

    # 初始化数据库
    Thread(target=load_db, args=(filePath,)).start()
    time.sleep(10)

    # 初始化第一个时间片的控制器
    cslot = ctrlslot(filePath + '/config')
    print("--生成控制器连接sh脚本")
    cslot.config2sh()
    print("--将第一个时间片的控制器放入topo")
    cslot.ctrl_init()
    
    # time.sleep(10)
    # datactrl = cslot.ctrl_slot[0]
    # for ctrl in datactrl:
    #     for sw in datactrl[ctrl]:
    #         Thread(target=sw_connect_ctrl, args=(sw,ctrl)).start()