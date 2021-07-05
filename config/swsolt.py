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
    
    def diff_slot(self, filePath:str):
        # 查找不同时间片之间的拓扑变换
        slot_num = len(os.listdir(filePath)) - 1    # 获取时间片个数
        # 找到时间片之间的不同连接关系
        slot1 = swsolt.load_slot(filePath + "/test_" + str(0))  # 时间片文件名
        for slot_no in range(slot_num):
            self.data_slot[slot_no] = slot1   # 存储时间片的拓扑信息
            self.diff_data[slot_no] = dict()  # 每个时间片的链路信息用字典存储
            slot2 = swsolt.load_slot(filePath + "/test_" + str((slot_no+1)%slot_num))
            
            # 找出slot1和slot2的不同，并且在内存中存储起来，方便控制器的拓扑切换
            for sw in range(slot1.__len__()):
                self.diff_data[slot_no][sw] = list()    # 使用list存储需要改变的指令
                tmp = set()
                for adj_sw in slot1[sw]:  # 找出相同的链路
                    if(adj_sw in slot2[sw]):
                        if(slot1[sw][adj_sw] != slot2[sw][adj_sw]):   # 链路的时延改变
                            self.diff_data[slot_no][sw].append((0, adj_sw, slot2[sw][adj_sw]))
                        tmp.add(adj_sw)
                for adj_sw in slot1[sw]:  # 找出要删除的链路,-1表示要删除
                    if(adj_sw not in tmp):
                        self.diff_data[slot_no][sw].append((-1, adj_sw, slot1[sw][adj_sw]))
                for adj_sw in slot2[sw]:  # 找出要添加的链路，1表示要添加
                    if(adj_sw not in tmp):
                        self.diff_data[slot_no][sw].append((1, adj_sw, slot2[sw][adj_sw]))
            slot1 = slot2
    
    def start(self, filePath:str):
        self.diff_slot(filePath)


if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    dslot = swsolt(filePath + '/timeslot')
    count_all = 0
    for index in dslot.diff_data:
        tmp = 0
        for sw in dslot.diff_data[index]:
            if len(dslot.diff_data[index][sw]) == 0:
                continue
            for iusse in dslot.diff_data[index][sw]:
                if iusse[0] != 0:
                    tmp += 1
        print(tmp)
        print("\n")
        count_all += tmp
    print(count_all)