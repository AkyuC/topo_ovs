import os
from .rt_ctrl2db import rt_ctrl2db

class rt_ctrl2sw:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.rt_ctrl2sw_slot = dict() # 所有时间片的数据
        self.rt_sw2ctrl_slot = dict() # 所有时间片的数据
        self.rt_ctrl2sw_diff = dict() # 所有时间片的数据
        self.rt_sw2ctrl_diff = dict() # 所有时间片的数据
        self.start(filePath)

    def start(self, filePath:str):
        # 读取控制器和卫星交换机之间的默认路由信息
        self.slot_num = len(os.listdir(filePath))    # 获取时间片个数
        for index in range(self.slot_num):
            self.rt_ctrl2sw_slot[index] = rt_ctrl2sw.load_ctrl2sw(filePath + "/c2s_" + str(index))
            self.rt_sw2ctrl_slot[index] = rt_ctrl2sw.load_sw2ctrl(filePath + "/c2s_" + str(index))
        for index in range(self.slot_num):
            self.rt_ctrl2sw_diff[index] = rt_ctrl2sw.diff_ctrl2sw(self.rt_ctrl2sw_slot[index], \
                self.rt_ctrl2sw_slot[(index+1)%self.slot_num])
            self.rt_sw2ctrl_diff[index] = rt_ctrl2sw.diff_sw2ctrl(self.rt_sw2ctrl_slot[index], \
                self.rt_sw2ctrl_slot[(index+1)%self.slot_num])

    @staticmethod
    def load_ctrl2sw(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        return rt_ctrl2db.load_db2ctrl(filename)
    
    @staticmethod
    def diff_ctrl2sw(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        return rt_ctrl2db.diff_ctrl2db(dslot_b, dslot_n)
    
    @staticmethod
    def load_sw2ctrl(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        return rt_ctrl2db.load_ctrl2db(filename)
    
    @staticmethod
    def diff_sw2ctrl(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        data = dict()
        for sw in dslot_b:
            data[sw] = list()
            if sw not in dslot_n:
                for rt in dslot_b[sw]:
                    data[sw].append((-1, rt[0], rt[1], rt[2]))
                continue
            for rt in dslot_b[sw]:    # 之前有，现在没有了
                if rt not in dslot_n[sw]:
                    data[sw].append((-1, rt[0], rt[1], rt[2]))
            for rt in dslot_n[sw]:    # 之前没有，现在有了
                if rt not in dslot_b[sw]:
                    data[sw].append((1, rt[0], rt[1], rt[2]))
        for sw in dslot_n:
            if sw not in dslot_b:
                data[sw] = list()
                for rt in dslot_n[sw]:
                    data[sw].append((1, rt[0], rt[1], rt[2]))
        return data

    @staticmethod
    def load_rt_ctrl2sw(ctrl2sw:dict, sw2ctrl:dict):
        # 初始化控制器和交换机之间的路由
        for ctrl in ctrl2sw:
            for rt in ctrl2sw[ctrl]:
                # sw_dst = rt[0]
                # sw = rt[1]
                # port = rt[2]
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.67.{},nw_dst=192.168.66.{} action=output:{}\""\
                    .format(rt[1], rt[1], ctrl, rt[0], rt[2]))
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.67.{},nw_dst=192.168.66.{} action=output:{}\""\
                    .format(rt[1], rt[1], ctrl, rt[0], rt[2]))
        for sw in sw2ctrl:
            for rt in sw2ctrl[sw]:
                # ctrl = rt[0]
                # sw = rt[1]
                # port = rt[2]
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.66.{},nw_dst=192.168.67.{} action=output:{}\""\
                    .format(rt[1], rt[1], sw, rt[0], rt[2]))
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.66.{},nw_dst=192.168.67.{} action=output:{}\""\
                    .format(rt[1], rt[1], sw, rt[0], rt[2]))
    
    @staticmethod
    def delete_rt_ctrl2sw(ctrl2sw:dict, sw2ctrl:dict):
        # 时间片切换，删除控制器和交换机之间下个时间片没有的路由
        for ctrl in ctrl2sw:
            for rt in ctrl2sw[ctrl]:
                if rt[0] == -1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.67.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.67.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
        for sw in sw2ctrl:
            for rt in sw2ctrl[sw]:
                if rt[0] == -1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.66.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.66.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
    
    @staticmethod
    def add_rt_ctrl2sw(ctrl2sw:dict, sw2ctrl:dict):
        # 时间片切换，添加控制器和交换机之间上个时间片没有的路由
        for ctrl in ctrl2sw:
            for rt in ctrl2sw[ctrl]:
                if rt[0] == 1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.67.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.67.{},nw_dst=192.168.66.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
        for sw in sw2ctrl:
            for rt in sw2ctrl[sw]:
                if rt[0] == 1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.66.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.66.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], sw, rt[1], rt[3]))

if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    rt_c2s = rt_ctrl2sw(filePath + "/rt_ctrl2sw")

    for slot_n in range(rt_c2s.slot_num):
        print("第{}个时间片".format(slot_n))
        for ctrl in rt_c2s.rt_ctrl2sw_slot[slot_n]:
            tmp = dict()
            for iusse in rt_c2s.rt_ctrl2sw_slot[slot_n][ctrl]:
                if iusse[0] not in tmp:
                    tmp[iusse[0]] = 0
                tmp[iusse[0]] += 1
            for sw in tmp:
                print("控制器{}到卫星交换机{}的路由，有{}跳".format(ctrl, sw, tmp[sw]))
        
        for ctrl in rt_c2s.rt_ctrl2sw_diff[slot_n]:
            tmp_add = dict()
            tmp_del = dict()
            if len(rt_c2s.rt_ctrl2sw_diff[slot_n][ctrl])==0:continue
            for iusse in rt_c2s.rt_ctrl2sw_diff[slot_n][ctrl]:
                if iusse[1] not in tmp_add:
                    tmp_add[iusse[1]] = 0
                    tmp_del[iusse[1]] = 0
                if iusse[0] == 1:
                    tmp_add[iusse[1]] += 1
                else:
                    tmp_del[iusse[1]] += 1
            for sw in tmp_add:
                print("时间片切换，控制器{}到卫星交换机{}的路由，需要添加{}条，删除{}条".format(ctrl, \
                    sw, tmp_add[sw], tmp_del[sw]))
        
        for sw in rt_c2s.rt_sw2ctrl_slot[slot_n]:
            print("卫星交换机{}到控制器{}的路由，有{}跳".format(sw, \
                rt_c2s.rt_sw2ctrl_slot[slot_n][sw][0][0], len(rt_c2s.rt_sw2ctrl_slot[slot_n][sw])))
            
        for sw in rt_c2s.rt_sw2ctrl_diff[slot_n]:
            del_n = 0
            add_n = 0
            if len(rt_c2s.rt_sw2ctrl_diff[slot_n][sw])==0:continue
            for iusse in rt_c2s.rt_sw2ctrl_diff[slot_n][sw]:
                if iusse[0] == 1:
                    add_n += 1
                else:
                    del_n += 1
            print("时间片切换，卫星交换机{}到控制器{}的路由，需要添加{}条，删除{}条".format(sw, \
                rt_c2s.rt_sw2ctrl_diff[slot_n][ctrl][0][1], add_n, del_n))
        
        print(" ")