import os
from typing import Set
from threading import Timer
import random

class nsbuilder:
    ns_set = Set()
    is_stoped = True

    @staticmethod
    def add_ns(num):
        # 添加ns，num为数量
        for i in range(num):
            if "h{}".format(i) not in nsbuilder.ns_set:
                os.system("ip netns add h{}".format(i))
                nsbuilder.ns_set.add("h{}".format(i))
    
    @staticmethod
    def del_ns(ns):
        # 删除某个ns
        os.system("ip netns del {}".format(ns))
        nsbuilder.ns_set.remove(ns)

    @staticmethod
    def clear():
        # 清空
        for ns in nsbuilder.ns_set:
            os.system("ip netns del {}".format(ns))
        nsbuilder.ns_set.clear()

    @staticmethod
    def __random_ping_period():
        if(nsbuilder.is_stoped):
            return False
        rs = random.sample(list(nsbuilder.ns_set, 2))
        os.system("ip netns exec {} ping -c 30 192.168.66.{}".format(rs[0], rs[1][1:-1]))
        Timer(1, nsbuilder.__random_ping_period).start()
    
    @staticmethod
    def random_ping_period():
        # 定时随机ping
        if(not nsbuilder.is_stoped):
            return False
        nsbuilder.is_stoped = False
        Timer(1, nsbuilder.__random_ping_period).start()

    @staticmethod
    def stop():
        nsbuilder.is_stoped = True