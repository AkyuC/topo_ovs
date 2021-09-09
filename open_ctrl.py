import os
from controller.controller import controller

# host的ip为192.168.66.x，控制器的ip为192.168.67.x，数据库的ip为192.168.68.x
if __name__ == '__main__' :
    #获取当前文件路径，读取配置文件需要
    os.system("sudo ovs-vsctl show > /dev/null")
    filePath = os.path.dirname(__file__)

    # 控制调度器加载
    ctrl = controller(filePath)