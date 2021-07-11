import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from .rt_ctrl2db import rt_ctrl2db
from .rt_ctrl2sw import rt_ctrl2sw
from .rt_db2db import rt_db2db
from .rt_sw2sw import rt_sw2sw


class rt_default:
    def __init__(self, filePath:str) -> None:
        self.rt_ctrl2db = rt_ctrl2db(filePath + "/rt_ctrl2db")
        self.rt_ctrl2sw = rt_ctrl2sw(filePath + "/rt_ctrl2sw")
        self.rt_db2db = rt_db2db(filePath + "/rt_db2db")
        self.rt_sw2sw = rt_sw2sw(filePath + "/rt_sw2sw")
        self.sw_flow_data = dict()
        self.sw_flow_diff_del= dict()
        self.sw_flow_diff_add= dict()
        self.sw_num = len(self.rt_sw2sw.rt_sw2sw_slot[0])
        self.slot_num = self.rt_sw2sw.slot_num
        self.filePath = filePath
        self.start()

    def start(self):
        # 将配置文件读出之后，转换为在每一个卫星交换机上下发的流表项
        for slot_no in range(self.slot_num):    # 初始化
            self.sw_flow_data[slot_no] = dict()
            self.sw_flow_diff_del[slot_no] = dict()
            self.sw_flow_diff_add[slot_no] = dict()
            for sw in range(self.sw_num):
                self.sw_flow_data[slot_no][sw] = list()
                self.sw_flow_diff_del[slot_no][sw] = list()
                self.sw_flow_diff_add[slot_no][sw] = list()
        
        for slot_no in range(self.slot_num): 
            # 先是转换控制器到所属的数据库的路由，设置为类型1（总共有六种），操作为添加1（0为修改时延，-1为删除）
            for ctrl in self.rt_ctrl2db.rt_ctrl2db_slot[slot_no]:
                for rt in self.rt_ctrl2db.rt_ctrl2db_slot[slot_no][ctrl]:
                    # rt为其中的一个路由表项,是一个元组,(db, sw, outport)
                    # 转化后的元组为(类型，源地址，目的地址，出端口)
                    self.sw_flow_data[slot_no][rt[1]].append((1,ctrl,rt[0],rt[2]))
            for ctrl in self.rt_ctrl2db.rt_ctrl2db_diff[slot_no]:
                for rt in self.rt_ctrl2db.rt_ctrl2db_diff[slot_no][ctrl]:
                    # 这里是时间片切换的时候，需要增删修改的路由表项
                    # rt的结构为（操作，目的，卫星交换机，时延）
                    # 转化后的元组为(操作，类型，源地址，目的地址，出端口)
                    if rt[0] == -1:
                        self.sw_flow_diff_del[slot_no][rt[2]].append((1,ctrl,rt[1],rt[3]))
                    if rt[0] == 1:
                        self.sw_flow_diff_add[slot_no][rt[2]].append((1,ctrl,rt[1],rt[3]))
        
            # 转化数据库到和下面的控制器器的路由，为类型2
            for db in self.rt_ctrl2db.rt_db2ctrl_slot[slot_no]:
                for rt in self.rt_ctrl2db.rt_db2ctrl_slot[slot_no][db]:
                    self.sw_flow_data[slot_no][rt[1]].append((2,db,rt[0],rt[2]))
            for db in self.rt_ctrl2db.rt_db2ctrl_diff[slot_no]:
                for rt in self.rt_ctrl2db.rt_db2ctrl_diff[slot_no][db]:
                    if rt[0] == -1:
                        self.sw_flow_diff_del[slot_no][rt[2]].append((2,db,rt[1],rt[3]))
                    if rt[0] == 1:
                        self.sw_flow_diff_add[slot_no][rt[2]].append((2,db,rt[1],rt[3]))
            
            # 转换控制器到所控制的交换机的路由，为类型3
            for ctrl in self.rt_ctrl2sw.rt_ctrl2sw_slot[slot_no]:
                for rt in self.rt_ctrl2sw.rt_ctrl2sw_slot[slot_no][ctrl]:
                    self.sw_flow_data[slot_no][rt[1]].append((3,ctrl,rt[0],rt[2]))
            for ctrl in self.rt_ctrl2sw.rt_ctrl2sw_diff[slot_no]:
                for rt in self.rt_ctrl2sw.rt_ctrl2sw_diff[slot_no][ctrl]:
                    if rt[0] == -1:
                        self.sw_flow_diff_del[slot_no][rt[2]].append((3,ctrl,rt[1],rt[3]))
                    if rt[0] == 1:
                        self.sw_flow_diff_add[slot_no][rt[2]].append((3,ctrl,rt[1],rt[3]))
            
            # 转换交换机到所属的控制器的路由，为类型4
            for sw in self.rt_ctrl2sw.rt_sw2ctrl_slot[slot_no]:
                for rt in self.rt_ctrl2sw.rt_sw2ctrl_slot[slot_no][sw]:
                    self.sw_flow_data[slot_no][rt[1]].append((4,sw,rt[0],rt[2]))
            for sw in self.rt_ctrl2sw.rt_ctrl2sw_diff[slot_no]:
                for rt in self.rt_ctrl2sw.rt_ctrl2sw_diff[slot_no][sw]:
                    if rt[0] == -1:
                        self.sw_flow_diff_del[slot_no][rt[2]].append((4,sw,rt[1],rt[3]))
                    if rt[0] == 1:
                        self.sw_flow_diff_add[slot_no][rt[2]].append((4,sw,rt[1],rt[3]))
            
            # 转换数据库到数据库的路由，为类型5
            for db in self.rt_db2db.rt_db2db_slot[slot_no]:
                for rt in self.rt_db2db.rt_db2db_slot[slot_no][db]:
                    self.sw_flow_data[slot_no][rt[1]].append((5,db,rt[0],rt[2]))
            for db in self.rt_db2db.rt_db2db_diff[slot_no]:
                for rt in self.rt_db2db.rt_db2db_diff[slot_no][db]:
                    if rt[0] == -1:
                        self.sw_flow_diff_del[slot_no][rt[2]].append((5,db,rt[1],rt[3]))
                    if rt[0] == 1:
                        self.sw_flow_diff_add[slot_no][rt[2]].append((5,db,rt[1],rt[3]))
            
            # 转换交换机到交换机的路由，为类型6
            for sw in self.rt_sw2sw.rt_sw2sw_slot[slot_no]:
                for sw_dst in self.rt_sw2sw.rt_sw2sw_slot[slot_no][sw]:
                    for rt in self.rt_sw2sw.rt_sw2sw_slot[slot_no][sw][sw_dst]:
                        self.sw_flow_data[slot_no][rt[0]].append((6,sw,sw_dst,rt[1]))
            for sw in self.rt_sw2sw.rt_sw2sw_diff[slot_no]:
                for rt in self.rt_sw2sw.rt_sw2sw_diff[slot_no][sw]:
                    if rt[0] == -1:
                        self.sw_flow_diff_del[slot_no][rt[2]].append((6,sw,rt[1],rt[3]))
                    if rt[0] == 1:
                        self.sw_flow_diff_add[slot_no][rt[2]].append((6,sw,rt[1],rt[3]))

    def config2sh(self):
        with ThreadPoolExecutor(max_workers=self.sw_num) as pool:
            # 初始化的流表，转换为shell脚本
            all_task = []
            for sw in range(self.sw_num):
                all_task.append(pool.submit(rt_default.__config_a_init_sw, \
                    sw, self.sw_flow_data[0][sw], self.filePath + "/rt_shell/rt_s{}_init.sh".format(sw)))
            wait(all_task, return_when=ALL_COMPLETED)

            for slot_no in range(self.slot_num):
                # 需要删除的流表项，转换为shell较脚本
                all_task.clear()
                for sw in range(self.sw_num):
                    all_task.append(pool.submit(rt_default.__config_a_del_sw, \
                        sw, slot_no, self.sw_flow_diff_del[slot_no][sw], self.filePath + "/rt_shell/rt_s{}_del_slot{}.sh".format(sw,slot_no)))
                wait(all_task, return_when=ALL_COMPLETED)

                # 需要添加的流表项，转换为shell脚本
                all_task.clear()
                for sw in range(self.sw_num):
                    all_task.append(pool.submit(rt_default.__config_a_add_sw, \
                        sw, slot_no, self.sw_flow_diff_add[slot_no][sw], self.filePath + "/rt_shell/rt_s{}_add_slot{}.sh".format(sw,slot_no)))
                wait(all_task, return_when=ALL_COMPLETED)
                    
    @staticmethod
    def __config_a_init_sw(sw, dlist:list, filename:str):
        # 一个卫星交换机
        rt_default.__rt2sh_df(sw, dlist, filename)
        id = read_id("s{}".format(sw))
        os.system("sudo docker cp {} {}:/home".format(filename,id))
    
    @staticmethod
    def __config_a_del_sw(sw, slot_no, dlist:list, filename:str):
        # 一个卫星交换机
        rt_default.__rt2sh_del(sw, dlist, filename)
        id = read_id("s{}".format(sw))
        os.system("sudo docker cp {} {}:/home".format(filename,id))

    @staticmethod
    def __config_a_add_sw(sw, slot_no, dlist:list, filename:str):
        # 一个卫星交换机
        rt_default.__rt2sh_add(sw, dlist, filename)
        id = read_id("s{}".format(sw))
        os.system("sudo docker cp {} {}:/home".format(filename,id))

    @staticmethod
    def __rt2sh_df(sw, dlist:list, filename:str):
        # 一个卫星交换机初始化的流表shell脚本转换
        with open(filename, 'w+') as file:
            for rt in dlist:
                if rt[0] == 1:
                    src = 67
                    dst = 68
                elif rt[0] == 2:
                    src = 68
                    dst = 67
                elif rt[0] == 3:
                    src = 67
                    dst = 66
                elif rt[0] == 4:
                    src = 66
                    dst = 67
                elif rt[0] == 5:
                    src = 68
                    dst = 68
                elif rt[0] == 6:
                    src = 66
                    dst = 66
                # command = "ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.{}.{},nw_dst=192.168.{}.{} action=output:{}\"\n"\
                #     .format(sw,src,rt[1]+1,dst,rt[2]+1,rt[3])
                # command += "ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.{}.{},nw_dst=192.168.{}.{} action=output:{}\"\n"\
                #     .format(sw,src,rt[1]+1,dst,rt[2]+1,rt[3])
                command = "ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.{}.{} action=output:{}\"\n"\
                    .format(sw,dst,rt[2]+1,rt[3])
                command += "ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.{}.{} action=output:{}\"\n"\
                    .format(sw,dst,rt[2]+1,rt[3])
                file.write(command)
    
    @staticmethod
    def __rt2sh_del(sw, dlist:list, filename:str):
        # 时间片切换，删除一个交换机不需要的流表的shell脚本转换
        with open(filename, 'w+') as file:
            for rt in dlist:
                if rt[0] == 1:
                    src = 67
                    dst = 68
                elif rt[0] == 2:
                    src = 68
                    dst = 67
                elif rt[0] == 3:
                    src = 67
                    dst = 66
                elif rt[0] == 4:
                    src = 66
                    dst = 67
                elif rt[0] == 5:
                    src = 68
                    dst = 68
                elif rt[0] == 6:
                    src = 66
                    dst = 66
                command = "ovs-ofctl del-flows s{} \"ip,nw_dst=192.168.{}.{}\"\n"\
                    .format(sw,dst,rt[2]+1,rt[3])
                command = "ovs-ofctl del-flows s{} \"arp,nw_dst=192.168.{}.{}\"\n"\
                    .format(sw,dst,rt[2]+1,rt[3])
                file.write(command)
  
    @staticmethod
    def __rt2sh_add(sw, dlist:list, filename:str):
        # 时间片切换，修改一个交换机的默认流表的shell脚本转换
        with open(filename, 'w+') as file:
            for rt in dlist:
                if rt[0] == 1:
                    src = 67
                    dst = 68
                elif rt[0] == 2:
                    src = 68
                    dst = 67
                elif rt[0] == 3:
                    src = 67
                    dst = 66
                elif rt[0] == 4:
                    src = 66
                    dst = 67
                elif rt[0] == 5:
                    src = 68
                    dst = 68
                elif rt[0] == 6:
                    src = 66
                    dst = 66
                command = "ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.{}.{} action=output:{}\"\n"\
                    .format(sw,dst,rt[2]+1,rt[3])
                command += "ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.{}.{} action=output:{}\"\n"\
                    .format(sw,dst,rt[2]+1,rt[3])
                file.write(command)

    @staticmethod
    def __load_rt_a_default(sw):
        # 加载一个卫星交换机的路由
        os.system("sudo docker exec -it s{sw} chmod +x /home/rt_s{sw}_init.sh;\
            sudo docker exec -it s{sw} /bin/bash /home/rt_s{sw}_init.sh".format(sw=sw))

    def load_rt_default(self):
        # 并发的下发所有默认流表
        with ThreadPoolExecutor(max_workers=self.sw_num) as pool:
            all_task = []
            for sw in range(self.sw_num):
                all_task.append(pool.submit(rt_default.__load_rt_a_default, sw))
            wait(all_task, return_when=ALL_COMPLETED)

    @staticmethod
    def __del_rt_a_default(sw, slot_no):
        # 时间片切换，删除一个卫星交换机的路由
        os.system("sudo docker exec -it s{sw} chmod +x /home/rt_s{sw}_del_slot{slot_no}.sh;\
            sudo docker exec -it s{sw} /bin/bash /home/rt_s{sw}_del_slot{slot_no}.sh".format(sw=sw,slot_no=slot_no))

    def del_rt_default(self, slot_no):
        # 时间片切换，删除不需要的流表
        with ThreadPoolExecutor(max_workers=self.sw_num) as pool:
            all_task = []
            for sw in range(self.sw_num):
                all_task.append(pool.submit(rt_default.__del_rt_a_default, sw, slot_no))
            wait(all_task, return_when=ALL_COMPLETED)

    @staticmethod
    def __add_rt_a_default(sw, slot_no):
        # 时间片切换，添加一个卫星交换机的路由
        os.system("sudo docker exec -it s{sw} chmod +x /home/rt_s{sw}_add_slot{slot_no}.sh;\
            sudo docker exec -it s{sw} /bin/bash /home/rt_s{sw}_add_slot{slot_no}.sh".format(sw=sw,slot_no=slot_no))

    def add_rt_default(self, slot_no):
        # 时间片切换，并发的下发修改所有默认流表
        with ThreadPoolExecutor(max_workers=self.sw_num) as pool:
            all_task = []
            for sw in range(self.sw_num):
                all_task.append(pool.submit(rt_default.__add_rt_a_default, sw, slot_no))
            wait(all_task, return_when=ALL_COMPLETED)

def read_id(docker_name:str):
    # 从系统中读取容器的网络命名空间id，并返回
    os.system("echo $(sudo docker ps -aqf\"name=^{}$\") > {}"\
        .format(docker_name,docker_name))
    with open(docker_name) as file:
        line = file.readline().strip()
        os.system("rm {}".format(docker_name))
        return line