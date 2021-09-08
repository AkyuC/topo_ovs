# /usr/sbin/dynomite
# /usr/bin/redis-cli    /usr/bin/redis-server
import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED


class dbload:
    def __init__(self, filePath:str) -> None:
        self.filePath = filePath
        with open(file=filePath+"/rt_ctrl2db/db_deploy") as file:
            lines = file.read().splitlines()
            self.db_num = int((lines[0].strip(' ').split(' '))[0]) # 获取分布式数据库的数量
            self.db_data = list(map(int, lines[1].strip(' ').split(' ')))    # 获取分布式数据库的位置

    def load_db(self):
        with ThreadPoolExecutor(max_workers=self.db_num) as pool:
            # 初始化的流表，转换为shell脚本
            all_task = []
            for db in self.db_data:
                all_task.append(pool.submit(dbload.__load_db_link, self.filePath, db))
            wait(all_task, return_when=ALL_COMPLETED)

    @staticmethod
    def __load_db_link(filePath, db):
        # 建立数据库和交换机之间的链路
        p1 = "s{}-db{}".format(db, db)
        p2 = "db{}-s{}".format(db, db) 
        os.system("sudo docker start db{} > /dev/null;\
            sudo ip link add {} type veth peer name {}".format(db, p1, p2))
        os.system("sudo ip link set dev {p1} name {p1} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{db}); \
                sudo ip link set dev {p2} name {p2} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' db{db});"\
                .format(db=db,p1=p1,p2=p2))
        os.system("sudo docker exec -it s{} ip link set dev {} up".format(db, p1))
        os.system("sudo docker exec -it db{} ip link set dev {} up".format(db, p2))
        os.system("sudo docker exec -it db{} ifconfig {} 192.168.68.{} netmask 255.255.0.0 up".format(db, p2, db+1))
        # 设置数据库的默认路由
        os.system("sudo docker exec -it db{} ip route flush table main".format(db))
        os.system("sudo docker exec -it db{} route add default dev {}".format(db, p2))
        # docker中的ovs连接端口
        os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null".\
            format(db, db, p1, p1, 4000+db))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,idle_timeout=65535,priority=20,ip,nw_dst=192.168.68.{} action=output:{}\""\
            .format(db, db, db+1, db+4000))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,idle_timeout=65535,priority=20,arp,nw_dst=192.168.68.{} action=output:{}\""\
            .format(db, db, db+1, db+4000))
        # 分布式数据库的配置文件
        os.system("sudo docker cp {}/db_conf/db{}.sh $(sudo docker ps -aqf\"name=^db{}$\"):/home"\
            .format(filePath,db,db))
        os.system("sudo docker cp {}/db_conf/redis{}.conf $(sudo docker ps -aqf\"name=^db{}$\"):/home"\
            .format(filePath,db,db))
        os.system("sudo docker cp {}/db_conf/dyno_{}.yml $(sudo docker ps -aqf\"name=^db{}$\"):/home"\
            .format(filePath,db,db))
        os.system("sudo docker cp {}/db_conf/monitor{} $(sudo docker ps -aqf\"name=^db{}$\"):/home"\
            .format(filePath,db,db))
        os.system("sudo docker exec -it db{db} chmod +x /home/db{db}.sh".format(db=db))
        os.system("sudo docker exec -it db{db} /bin/bash /home/db{db}.sh start".format(db=db))
        os.system("sudo docker exec -it db{db} chmod +x /home/monitor{db}".format(db=db))
        os.system("sudo docker exec -it db{db} /home/monitor{db}".format(db=db))