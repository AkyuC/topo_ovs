import os
from threading import Timer
import random

class flowbuilder:
    count = 0
    is_stoped = True

    @staticmethod
    def __random_iperf_period():
        if(flowbuilder.is_stoped):
            return False
        rs = random.sample(range(0, flowbuilder.count-1), 2)
        os.system("sudo docker exec -it s{} iperf -u -s".format(rs[0]))
        os.system("sudo docker exec -it s{} iperf -u -c 192.168.66.{} -b 20M -t 5"\
            .format(rs[1], int(rs[0])+1))
        Timer(1, flowbuilder.__random_iperf_period).start()
    
    @staticmethod
    def random_iperf_period(num):
        # 定时随机iperf
        flowbuilder.count = num
        if(not flowbuilder.is_stoped):
            return False
        flowbuilder.is_stoped = False
        Timer(1, flowbuilder.__random_iperf_period).start()

    @staticmethod
    def stop():
        flowbuilder.is_stoped = True