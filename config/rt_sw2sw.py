import os
from .rt_db2db import rt_db2db


class rt_sw2sw:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.rt_sw2sw_slot = dict() # 所有时间片的数据
        self.rt_sw2sw_slot0 = rt_db2db.load_db2db(filePath + "/s2s_0")
        self.rt_sw2sw_diff = dict() # 所有时间片的数据
        self.start(filePath)

    def start(self, filePath:str):
        # 读取分布式数据库之间的默认路由信息
        self.slot_num = len(os.listdir(filePath))    # 获取时间片个数
        for index in range(self.slot_num):
            self.rt_sw2sw_slot[index] = rt_sw2sw.load_sw2sw(filePath + "/s2s_" + str(index))
        for index in range(self.slot_num):
            self.rt_sw2sw_diff[index] = rt_sw2sw.diff_sw2sw(self.rt_sw2sw_slot[index], \
                self.rt_sw2sw_slot[(index+1)%self.slot_num])

    @staticmethod
    def load_sw2sw(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()
        with open(file=filename) as file:
            lines = file.read().splitlines()
            for line in lines:
                line_list = line.strip(' ').split(' ')
                sw1 = int(line_list[0])
                if len(line_list)==1:
                    data[sw1] = dict()
                    continue
                sw2 = int(line_list[1])
                if sw2 not in data[sw1]:
                    data[sw1][sw2] = list()
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw
                    data[sw1][sw2].append((sw, port+1000))

        return data
        
    @staticmethod
    def diff_sw2sw(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        data = dict()
        for sw in dslot_b:
            data[sw] = list()
            for adj_sw in dslot_b[sw]:
                for rt in dslot_b[sw][adj_sw]:
                    if rt not in dslot_n[sw][adj_sw]:
                        data[sw].append((-1, adj_sw, rt[0], rt[1]))
            for adj_sw in dslot_n[sw]:
                for rt in dslot_n[sw][adj_sw]:
                    if rt not in dslot_b[sw][adj_sw]:
                        data[sw].append((1, adj_sw, rt[0], rt[1]))
        return data
    
    @staticmethod
    def load_rt_sw2sw(sw2sw:dict):
        # 初始化交换机和交换机之间的路由
        for sw in sw2sw:
            for rt in sw2sw[sw]:
                # sw_dst = rt[0]
                # sw = rt[1]
                # port = rt[2]
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.66.{},nw_dst=192.168.66.{} action=output:{}\""\
                    .format(rt[1], rt[1], sw, rt[0], rt[2]))
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.66.{},nw_dst=192.168.66.{} action=output:{}\""\
                    .format(rt[1], rt[1], sw, rt[0], rt[2]))
    
    @staticmethod
    def delete_rt_sw2sw(sw2sw:dict):
        # 时间片切换，删除交换机和交换机之间下个时间片没有的路由
        for sw in sw2sw:
            for rt in sw2sw[sw]:
                if rt[0] == -1: # 删除条目
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.66.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.66.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
    
    @staticmethod
    def add_rt_sw2sw(sw2sw:dict):
        # 时间片切换，添加交换机和交换机之间上个时间片没有的路由
        for sw in sw2sw:
            for rt in sw2sw[sw]:
                if rt[0] == 1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.66.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.66.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
