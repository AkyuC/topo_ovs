# /usr/sbin/dynomite
# /usr/bin/redis-cli    /usr/bin/redis-server
import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED


class dbload:
    def __init__(self, filename:str) -> None:
        with open(file=filename) as file:
            lines = file.read().splitlines()
            self.db_num = int((lines[0].strip(' ').split(' '))[0]) # 获取分布式数据库的数量
            self.db_data = list(map(int, lines[1].strip(' ').split(' ')))    # 获取分布式数据库的位置

    def load_db(self):
        with ThreadPoolExecutor(max_workers=self.db_num) as pool:
            # 初始化的流表，转换为shell脚本
            all_task = []
            for db in self.db_data:
                all_task.append(pool.submit(dbload.__load_db_link, db))
            wait(all_task, return_when=ALL_COMPLETED)

    @staticmethod
    def __load_db_link(sw):
        # 建立数据库和交换机之间的链路
        p1 = "s{}-db{}".format(sw, sw)
        p2 = "db{}-s{}".format(sw, sw) 
        os.system("sudo docker start db{};\
            sudo ip link add {} type veth peer name {}".format(sw, p1, p2))
        os.system("ovspid=$(sudo docker inspect -f '{{{{.State.Pid}}}}' s{sw}); \
                dbpid=$(sudo docker inspect -f '{{{{.State.Pid}}}}' db{sw}); \
                sudo ip link set dev {p1} name {p1} netns ${{ovspid}} \
                sudo ip link set dev {p2} name {p2} netns ${{dbpid}}"\
                .format(sw=sw,p1=p1,p2=p2))
        os.system("sudo docker exec -it s{} ip link set dev {} up".format(sw, p1))
        os.system("sudo docker exec -it db{} ip link set dev {} up".format(sw, p2))
        os.system("sudo docker exec -it db{} ip addr add 192.168.68.{} dev {}".format(sw, sw+1, p2))
        # 设置数据库的默认路由
        os.system("sudo docker exec -it db{} ip route flush table main".format(sw))
        os.system("sudo docker exec -it db{} route add default dev {}".format(sw, p2))
        # docker中的ovs连接端口
        os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null".\
            format(sw, sw, p1, p1, 4000+sw))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.68.{} action=output:{}\""\
            .format(sw, sw, sw+1, sw+4000))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.68.{} action=output:{}\""\
            .format(sw, sw, sw+1, sw+4000))