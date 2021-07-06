from .command_queue import command_queue
from threading import Timer
from ..utils import const_command

# 定时切换
class timer:
    def __init__(self, timefile:str) -> None:
        # 加载时间片序列
        self.time_list = list()
        self.index = 0  # 第0个时间片
        self.slot_num = 0  # 时间片个数
        self.is_stoped = True  # 是否已经停止
        self.load_time_seq(timefile)

    def send_timer_command(self):
        # 向控制器发送命令，说明需要切换时间片
        command_queue.write_queue((const_command.timer_diff, self.index))
        if(self.is_stoped):
            return False
        tmp  = self.index
        self.index = (self.index + 1) % self.slot_num
        Timer(self.time_list[tmp], self.send_timer_command).start()

    def start(self):
        if(not self.is_stoped):
            return False
        self.is_stoped = False
        # 需要写入数据库目前所在的时间片
        Timer(self.time_list[self.index], self.send_timer_command).start()

    def stop(self):
        self.is_stoped = True

    def load_time_seq(self, timefile:str):
        # 文件操作，读写时间片序列，目前还没有这个数据，所以就自己设置了一个简单的，每个时间片之间都是90s切换
        with open(file=timefile) as file:
            line = file.readline().split()
            self.slot_num = len(line)
            for i in range(line.__len__()):
                self.time_list.append(int(line[i]))