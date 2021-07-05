import os


class rt_ctrl2db:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.rt_ctrl2db_slot = dict() # 所有时间片的数据
        self.rt_db2ctrl_slot = dict() # 所有时间片的数据
        self.rt_ctrl2db_diff = dict() # 所有切换时间片的数据
        self.rt_db2ctrl_diff = dict() # 所有切换时间片的数据
        self.start(filePath)

    def start(self, filePath:str):
        # 读取控制器和数据库之间的默认路由信息
        self.slot_num = len(os.listdir(filePath))    # 获取时间片个数
        for index in range(self.slot_num):
            self.rt_ctrl2db_slot[index] = rt_ctrl2db.load_ctrl2db(filePath + "/c2d_" + str(index))
            self.rt_db2ctrl_slot[index] = rt_ctrl2db.load_db2ctrl(filePath + "/c2d_" + str(index))
        for index in range(self.slot_num):
            self.rt_ctrl2db_diff[index] = rt_ctrl2db.diff_ctrl2db(self.rt_ctrl2db_slot[index], \
                self.rt_ctrl2db_slot[(index+1)%self.slot_num])
            self.rt_db2ctrl_diff[index] = rt_ctrl2db.diff_db2ctrl(self.rt_db2ctrl_slot[index], \
                self.rt_db2ctrl_slot[(index+1)%self.slot_num])

    @staticmethod
    def load_ctrl2db(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()
        with open(file=filename) as file:
            lines = file.read().splitlines()
            for line in lines[1::2]:
                line_list = int, line.strip(' ').split(' ')
                ctrl = int(line_list[0])
                db = int(line_list[1])
                if ctrl not in data:
                    data[ctrl] = list()
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw
                    data[ctrl].append((db, sw, port+1000))
        return data

    @staticmethod
    def diff_ctrl2db(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        data = dict()
        for ctrl in dslot_b:
            data[ctrl] = list()
            if ctrl not in dslot_n: # 控制器ctrl消除了
                for rt in dslot_b[ctrl]:
                    data[ctrl].append((-1, rt[0], rt[1], rt[2]))
                continue
            for rt in dslot_b[ctrl]:    # 之前有，现在没有了
                if rt not in dslot_n[ctrl]:
                    data[ctrl].append((-1, rt[0], rt[1], rt[2]))
            for rt in dslot_n[ctrl]:    # 之前没有，现在有了
                if rt not in dslot_b[ctrl]:
                    data[ctrl].append((1, rt[0], rt[1], rt[2]))
        for ctrl in dslot_n:
            if ctrl not in dslot_b: # 新增了一个控制器
                data[ctrl] = list()
                for rt in dslot_b[ctrl]:
                    data[ctrl].append((1, rt[0], rt[1], rt[2]))
        return data

    @staticmethod
    def load_db2ctrl(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()
        with open(file=filename) as file:
            lines = file.read().splitlines()
            for line in lines[::2]:
                line_list = int, line.strip(' ').split(' ')
                db = int(line_list[0])
                ctrl = int(line_list[1])
                if db not in data:
                    data[db] = list()
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw
                    data[db].append((ctrl, sw, port+1000))
        return data
    
    @staticmethod
    def diff_db2ctrl(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        return rt_ctrl2db.diff_ctrl2db(dslot_b, dslot_n)

    @staticmethod
    def load_rt_ctrl2db(ctrl2db:dict, db2ctrl:dict):
        # 初始化控制器和数据库之间的路由
        for ctrl in ctrl2db:
            for rt in ctrl2db[ctrl]:
                # db = rt[0]
                # sw = rt[1]
                # port = rt[2]
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.67.{},nw_dst=192.168.68.{} action=output:{}\""\
                    .format(rt[1], rt[1], ctrl, rt[0], rt[2]))
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.67.{},nw_dst=192.168.68.{} action=output:{}\""\
                    .format(rt[1], rt[1], ctrl, rt[0], rt[2]))
        for db in db2ctrl:
            for rt in db2ctrl[db]:
                # ctrl = rt[0]
                # sw = rt[1]
                # port = rt[2]
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.67.{} action=output:{}\""\
                    .format(rt[1], rt[1], db, rt[0], rt[2]))
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.67.{} action=output:{}\""\
                    .format(rt[1], rt[1], db, rt[0], rt[2]))

    @staticmethod
    def delete_rt_ctrl2db(ctrl2db:dict, db2ctrl:dict):
        # 时间片切换，删除控制器和数据库之间在下一个时间片没有的路由
        for ctrl in ctrl2db:
            for rt in ctrl2db[ctrl]:
                if rt[0] == -1: # 删除条目
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.67.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.67.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
        for db in db2ctrl:
            for rt in db2ctrl[db]:
                if rt[0] == -1: # 删除条目
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))
    
    @staticmethod
    def add_rt_ctrl2db(ctrl2db:dict, db2ctrl:dict):
        # 时间片切换，添加控制器和数据库之间在上一个时间片没有的路由
        for ctrl in ctrl2db:
            for rt in ctrl2db[ctrl]:
                if rt[0] == 1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.67.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.67.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], ctrl, rt[1], rt[3]))
        for db in db2ctrl:
            for rt in db2ctrl[db]:
                if rt[0] == 1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.67.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))

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
            for rt in dslot_b[sw]:    # 之前有，现在没有了
                if rt not in dslot_n[sw]:
                    data[sw].append((-1, rt[0], rt[1], rt[2]))
            for rt in dslot_n[sw]:    # 之前没有，现在有了
                if rt not in dslot_b[sw]:
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

class rt_db2db:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.rt_db2db_slot = dict() # 所有时间片的数据
        self.rt_db2db_diff = dict() # 所有时间片的数据
        self.start(filePath)

    def start(self, filePath:str):
        # 读取分布式数据库之间的默认路由信息
        self.slot_num = len(os.listdir(filePath))    # 获取时间片个数
        for index in range(self.slot_num):
            self.rt_db2db_slot[index] = rt_db2db.load_db2db(filePath + "/d2d_" + str(index))
        for index in range(self.slot_num):
            self.rt_db2db_diff[index] = rt_db2db.diff_db2db(self.rt_db2db_slot[index], \
                self.rt_db2db_slot[(index+1)%self.slot_num])

    @staticmethod
    def load_db2db(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()
        with open(file=filename) as file:
            lines = file.read().splitlines()
            for line in lines:
                line_list = int, line.strip(' ').split(' ')
                db1 = int(line_list[0])
                if len(line_list)==1:
                    data[db1] = list()
                    continue
                db2 = int(line_list[1])
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw
                    data[db1].append((db2, sw, port+1000))
        return data
        
    @staticmethod
    def diff_db2db(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        return rt_ctrl2sw.diff_sw2ctrl(dslot_b, dslot_n)

    @staticmethod
    def load_rt_db2db(db2db:dict):
        # 初始化数据库和数据库之间的路由
        for db in db2db:
            for rt in db2db[db]:
                # db_dst = rt[0]
                # sw = rt[1]
                # port = rt[2]
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
                    .format(rt[1], rt[1], db, rt[0], rt[2]))
                os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
                    .format(rt[1], rt[1], db, rt[0], rt[2]))
    
    @staticmethod
    def delete_rt_db2db(db2db:dict):
        # 时间片切换，删除数据库和数据库之间下个时间片没有的路由
        for db in db2db:
            for rt in db2db[db]:
                if rt[0] == -1: # 删除条目
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))
    
    @staticmethod
    def add_rt_db2db(db2db:dict):
        # 时间片切换，添加数据库和数据库之间上个时间片没有的路由
        for db in db2db:
            for rt in db2db[db]:
                if rt[0] == 1: # 添加条目
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))
                    os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
                        .format(rt[2], rt[2], db, rt[1], rt[3]))


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
                line_list = int, line.strip(' ').split(' ')
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
