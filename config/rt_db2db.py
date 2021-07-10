import os
import threading


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
                line_list = line.strip(' ').split(' ')
                db1 = int(line_list[0])
                if len(line_list)==1:
                    data[db1] = list()
                    continue
                db2 = int(line_list[1])
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw*1000
                    data[db1].append((db2, sw, port+1000))
        return data
        
    @staticmethod
    def diff_db2db(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        data = dict()
        for db in dslot_b:
            data[db] = list()
            for rt in dslot_b[db]:
                if rt not in dslot_n[db]:
                    data[db].append((-1, rt[0], rt[1], rt[2]))
            for rt in dslot_n[db]:
                if rt not in dslot_b[db]:
                    data[db].append((1, rt[0], rt[1], rt[2]))
        return data

    # def __load_rt_a_db2db(*args):
    #     db = args[0]
    #     db2db = args[1]
    #     for rt in db2db:
    #         # db_dst = rt[0]
    #         # sw = rt[1]
    #         # port = rt[2]
    #         os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
    #             .format(rt[1], rt[1], db+1, rt[0]+1, rt[2]))
    #         os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
    #             .format(rt[1], rt[1], db+1, rt[0]+1, rt[2]))

    # @staticmethod
    # def load_rt_db2db(db2db:dict):
    #     # 初始化数据库和数据库之间的路由
    #     for db in db2db:
    #         threading.Thread(target=rt_db2db.__load_rt_a_db2db, args=(db, db2db[db],)).start()
    
    # def __delete_rt_a_db2db(*args):
    #     db = args[0]
    #     db2db = args[1]
    #     for rt in db2db:
    #         if rt[0] == -1: # 删除条目
    #             os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
    #                 .format(rt[2], rt[2], db+1, rt[1]+1, rt[3]))
    #             os.system("sudo docker exec -it s{} ovs-ofctl del-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
    #                 .format(rt[2], rt[2], db+1, rt[1]+1, rt[3]))

    # @staticmethod
    # def delete_rt_db2db(db2db:dict):
    #     # 时间片切换，删除数据库和数据库之间下个时间片没有的路由
    #     for db in db2db:
    #         threading.Thread(target=rt_db2db.__delete_rt_a_db2db, args=(db, db2db[db],)).start()
    
    # def __add_rt_a_db2db(*args):
    #     db = args[0]
    #     db2db = args[1]
    #     for rt in db2db:
    #         if rt[0] == 1: # 添加条目
    #             os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
    #                 .format(rt[2], rt[2], db+1, rt[1]+1, rt[3]))
    #             os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{} action=output:{}\""\
    #                 .format(rt[2], rt[2], db+1, rt[1]+1, rt[3]))
    
    # @staticmethod
    # def add_rt_db2db(db2db:dict):
    #     # 时间片切换，添加数据库和数据库之间上个时间片没有的路由
    #     for db in db2db:
    #         threading.Thread(target=rt_db2db.__add_rt_a_db2db, args=(db, db2db[db],)).start()                
    

if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    rt_d2d = rt_db2db(filePath + "/rt_db2db")

    for slot_n in range(rt_d2d.slot_num):
        print("第{}个时间片".format(slot_n))
        for db in rt_d2d.rt_db2db_slot[slot_n]:
            tmp = dict()
            for iusse in rt_d2d.rt_db2db_slot[slot_n][db]:
                if iusse[0] not in tmp:
                    tmp[iusse[0]] = 0
                tmp[iusse[0]] += 1
            for db_dst in tmp:
                print("数据库{}到数据库{}的路由，有{}跳".format(db, db_dst, tmp[db_dst]))
    
        for db in rt_d2d.rt_db2db_diff[slot_n]:
            tmp_add = dict()
            tmp_del = dict()
            if len(rt_d2d.rt_db2db_diff[slot_n][db])==0:continue
            for iusse in rt_d2d.rt_db2db_diff[slot_n][db]:
                if iusse[1] not in tmp_add:
                    tmp_add[iusse[1]] = 0
                    tmp_del[iusse[1]] = 0
                if iusse[0] == 1:
                    tmp_add[iusse[1]] += 1
                else:
                    tmp_del[iusse[1]] += 1
            for db_dst in tmp_add:
                print("时间片切换，数据库{}到数据库{}的路由，需要添加{}条，删除{}条".format(db, \
                    db_dst, tmp_add[db_dst], tmp_del[db_dst]))
        print(' ')