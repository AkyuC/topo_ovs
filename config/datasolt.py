import os


class datasolt:
    def __init__(self) -> None:
        self.slot_num = 0   # 时间片的个数
        self.data_slot = [] # 所有时间片的数据
        self.diff_data = [] # 存储不同时间片之间需要改变的链路信息
        self.slot0          # 第一个时间片数据

    def load_slot(self, filename:str):
        # 从文件当中加载一个时间片
        with open(file=filename) as file:
            lines = file.read().splitlines()
            sw_num = int(lines[0]) # 获取卫星交换机的数量
            del lines[0:2] # 删除前面的两行内容
        data = {}
        for i in range(sw_num):
            data[i] = []
        for line in lines:
            link = line.split(" ", 2)
            data[int(link[0])].append((int(link[1]), float(link[2])))
        return data
    
    def diff_slot(self, filePath:str):
        # 查找不同时间片之间的拓扑变换
        slot_num = len(os.listdir(filePath)) - 1    # 获取时间片个数
        # 找到时间片之间的不同连接关系
        slot1 = self.load_slot(filePath + "/test_" + str(0))  # 可能还需要修改文件名
        for i in range(slot_num):
            self.data_slot[i] = slot1   # 存储时间片的拓扑信息
            self.diff_data[i] = []  # 每个时间片的链路信息用字典存储
            slot2 = self.load_slot(filePath + "/test_" + str((i+1)%slot_num))
            # 找出slot1和slot2的不同，并且在内存中存储起来，方便控制器的拓扑切换
            for j in range(slot1.__len__()):
                tmp = []
                for k in range(len(slot1[j])):  # 找出相同的链路
                    if(slot1[j][k] in slot2[j]):
                        if(slot1[j][k][1] != slot2[j][slot2[j].index(k)][1]):   # 链路的时延改变
                            self.diff_data[i][j].append((0, slot1[j][k][0], slot2[j][slot2[j].index(k)][1]))
                        tmp.append(slot1[j][k])
                for k in range(len(slot1[j])):  # 找出要删除的链路,-1表示要删除
                    if(slot1[j][k] in tmp):
                        self.diff_data[i][j].append((-1, slot1[j][k][0], slot1[j][k][1]))
                for k in range(len(slot2[j])):  # 找出要添加的链路，1表示要添加
                    if(slot2[j][k] not in tmp):
                        self.diff_data[i][j].append((1, slot2[j][k][0], slot2[j][k][1]))
            slot1 = slot2
    
    def start(self, filePath:str):
        self.slot0 = self.load_slot(filePath + "/test_" + str(0))
        self.diff_slot(filePath)