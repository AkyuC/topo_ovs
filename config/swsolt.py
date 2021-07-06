import os


class swsolt:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.data_slot = dict() # 所有时间片的数据
        self.diff_data = dict() # 存储不同时间片之间需要改变的链路信息
        self.start(filePath)

    @staticmethod
    def load_slot(filename:str):
        # 从文件当中加载一个时间片
        sw_num = 0
        with open(file=filename) as file:
            lines = file.read().splitlines()
            sw_num = int(lines[0].strip('\n')) # 获取卫星交换机的数量
            del lines[0:2] # 删除前面的两行内容
        # 获取链路信息
        data = dict()
        for sw in range(sw_num):
            data[sw] = dict()
        for line in lines:
            link = line.strip(' ').split(" ")
            data[int(link[0])][int(link[1])] = float(link[2])
        return data
    
    @staticmethod
    def diff_slot(dslot_b:dict, dslot_n:dict):
        # 找到时间片之间的不同连接关系
        data = dict()
        for sw in dslot_b:
            data[sw] = list()
            for adj_sw in dslot_b[sw]:
                if adj_sw not in dslot_n[sw]:
                    data[sw].append((-1, sw, adj_sw, dslot_b[sw][adj_sw]))
                elif dslot_b[sw][adj_sw] != dslot_n[sw][adj_sw]:
                    data[sw].append((0, sw, adj_sw, dslot_n[sw][adj_sw]))
        for sw in dslot_n:
            for adj_sw in dslot_n[sw]:
                if adj_sw not in dslot_b[sw]:
                    data[sw].append((1, sw, adj_sw, dslot_n[sw][adj_sw]))
        return data
    
    def start(self, filePath:str):
        # 查找不同时间片之间的拓扑变换
        self.slot_num = len(os.listdir(filePath)) - 1    # 获取时间片个数
        for slot_no in range(self.slot_num):
            self.data_slot[slot_no] = swsolt.load_slot(filePath + "/test_" + str(slot_no))
        for slot_no in range(self.slot_num):
            self.diff_data[slot_no] = swsolt.diff_slot(self.data_slot[slot_no], self.data_slot[(slot_no+1)%self.slot_num])


if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    dslot = swsolt(filePath + '/timeslot')
    
    for index in dslot.data_slot:
        tmp = 0
        print("第{}个时间片:".format(index))
        for sw in dslot.data_slot[index]:
            tmp0 = 0
            tmp0 += len(dslot.data_slot[index][sw])
            # print("交换机{}有{}条边".format(sw, tmp0))
            tmp += tmp0
        print("有{}条边".format(int(tmp/2)))
        print("\n")
    print("\n")

    count_all = 0
    count_all0 = 0
    for index in dslot.diff_data:
        tmp = 0
        tmp0 = 0
        print("第{}个时间片:".format(index))
        for sw in dslot.diff_data[index]:
            if len(dslot.diff_data[index][sw]) == 0:
                continue
            for iusse in dslot.diff_data[index][sw]:
                if iusse[0] != 0:
                    tmp += 1
                else:
                    tmp0 += 1
        print("增删{}条边，修改{}条边".format(int(tmp/2), int(tmp0/2)))
        print("\n")
        count_all += tmp
        count_all0 += tmp0
    print("总共增删{}条边，修改{}条边".format(int(count_all/2), int(count_all0/2)))