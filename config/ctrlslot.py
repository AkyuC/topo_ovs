import os
from typing import Dict


class ctrlslot:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.ctrl_slot = Dict() # 所有时间片的数据
        self.start(filePath)
    
    @staticmethod
    def load_ctrl(filename:str):
        # 从文件当中加载一个时间片的控制器位置信息
        ctrl_num = 0
        with open(file=filename) as file:
            lines = file.read().splitlines()
            ctrl_num = int(lines[0]) # 获取控制器的数量
            del lines[0:1] # 删除前面的一行内容
        # 获取链路信息
        data = Dict()
        ctrl = lines[::2]       # 控制器所在的卫星交换机的编号
        ctrlsw = lines[1::2]    # 控制器控制的卫星交换机编号
        for index in range(ctrl_num):
            data[int(ctrl[index])] = list(map(int, ctrlsw[index].split(' ')))
        return data

    def start(self, filePath:str):
        self.slot_num = len(os.listdir(filePath))    # 获取时间片个数
        for index in range(self.slot_num):
            self.ctrl_slot[index] = ctrlslot.load_ctrl(filePath + "ctrl_" + str(index))