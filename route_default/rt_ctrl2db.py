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
        self.slot_num = len(os.listdir(filePath)) - 1    # 获取时间片个数
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
                line_list = line.strip(' ').split(' ')
                ctrl = int(line_list[0])
                db = int(line_list[1])
                if ctrl not in data:
                    data[ctrl] = list()
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw*1000
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
                for rt in dslot_n[ctrl]:
                    data[ctrl].append((1, rt[0], rt[1], rt[2]))
        return data

    @staticmethod
    def load_db2ctrl(filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()
        with open(file=filename) as file:
            lines = file.read().splitlines()
            for line in lines[::2]:
                line_list = line.strip(' ').split(' ')
                db = int(line_list[0])
                ctrl = int(line_list[1])
                if db not in data:
                    data[db] = list()
                for i in range(len(line_list)-2):
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw*1000
                    data[db].append((ctrl, sw, port+1000))
        return data
    
    @staticmethod
    def diff_db2ctrl(dslot_b:dict, dslot_n:dict):
        # 找出两个时间片的路由的增删
        return rt_ctrl2db.diff_ctrl2db(dslot_b, dslot_n)



if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    rt_c2b = rt_ctrl2db(filePath + "/rt_ctrl2db")

    for slot_n in range(rt_c2b.slot_num):
        print("第{}个时间片".format(slot_n))
        for ctrl in rt_c2b.rt_ctrl2db_slot[slot_n]:
            print("控制器{}到数据库{}的路由，有{}跳".format(ctrl, \
                rt_c2b.rt_ctrl2db_slot[slot_n][ctrl][0][0], len(rt_c2b.rt_ctrl2db_slot[slot_n][ctrl])))
        
        for db in rt_c2b.rt_db2ctrl_slot[slot_n]:
            tmp = dict()
            for iusse in rt_c2b.rt_db2ctrl_slot[slot_n][db]:
                if iusse[0] not in tmp:
                    tmp[iusse[0]] = 0
                tmp[iusse[0]] += 1
            for ctrl in tmp:
                print("数据库{}到控制器{}的路由，有{}跳".format(db, ctrl, tmp[ctrl]))

        for ctrl in rt_c2b.rt_db2ctrl_diff[slot_n]:
            del_n = 0
            add_n = 0
            if len(rt_c2b.rt_db2ctrl_diff[slot_n][ctrl])==0:continue
            for iusse in rt_c2b.rt_db2ctrl_diff[slot_n][ctrl]:
                if iusse[0] == 1:
                    add_n += 1
                else:
                    del_n += 1
            print("时间片切换，控制器{}到数据库{}的路由，需要添加{}条，删除{}条".format(ctrl, \
                rt_c2b.rt_db2ctrl_diff[slot_n][ctrl][0][1], add_n, del_n))
        
        for db in rt_c2b.rt_db2ctrl_diff[slot_n]:
            tmp_add = dict()
            tmp_del = dict()
            if len(rt_c2b.rt_db2ctrl_diff[slot_n][db])==0:continue
            for iusse in rt_c2b.rt_db2ctrl_diff[slot_n][db]:
                if iusse[1] not in tmp_add:
                    tmp_add[iusse[1]] = 0
                    tmp_del[iusse[1]] = 0
                if iusse[0] == 1:
                    tmp_add[iusse[1]] += 1
                else:
                    tmp_del[iusse[1]] += 1
            for ctrl in tmp_add:
                print("时间片切换，数据库{}到控制器{}的路由，需要添加{}条，删除{}条".format(db, \
                    ctrl, tmp_add[ctrl], tmp_del[ctrl]))
        
        print(" ")