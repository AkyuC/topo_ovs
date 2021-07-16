import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED


class swslot:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.data_slot = dict() # 所有时间片的数据
        self.diff_data = dict() # 存储不同时间片之间需要改变的链路信息
        self.filePath = filePath
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
        self.slot_num = len(os.listdir(filePath + "/timeslot")) - 1    # 获取时间片个数
        for slot_no in range(self.slot_num):
            self.data_slot[slot_no] = swslot.load_slot(filePath + "/timeslot/test_" + str(slot_no))
        for slot_no in range(self.slot_num):
            self.diff_data[slot_no] = swslot.diff_slot(self.data_slot[slot_no], self.data_slot[(slot_no+1)%self.slot_num])

    def cpsh2docker(self):
        data = self.data_slot[0]
        for sw in data:
            os.system("sudo docker cp {}/sw_shell/sw{}_link_init.sh $(sudo docker ps -aqf\"name=^s{}$\"):/home"\
                .format(self.filePath,sw,sw))
        for slot_no in range(self.slot_num):
            for sw in self.diff_data[slot_no]:
                filename = self.filePath + "/sw_shell/s{}_change_dc_slot{}.sh".format(sw,slot_no)
                os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home".format(filename,sw))
            for sw in self.diff_data[slot_no]:
                filename = self.filePath + "/sw_shell/s{}_change_add_slot{}.sh".format(sw,slot_no)
                os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home".format(filename,sw))

    def config2sh(self):
        links_set = set()
        data = self.data_slot[0]
        for sw in data:
            with open(self.filePath + "/sw_shell/sw{}_link_init.sh".format(sw), 'w+') as file:
                file.write("chmod +x /home/ovs_open.sh; ./home/ovs_open.sh > /dev/null\n")
                file.write("ovs-vsctl add-br s{} -- set bridge s{} protocols=OpenFlow10,OpenFlow11,OpenFlow12,OpenFlow13 other-config:datapath-id={}\n".format(
                        sw, sw, sw))
                # 添加本地端口和默认路由
                p1 = "s{}-h{}".format(sw, sw)
                p2 = "h{}-s{}".format(sw, sw)
                file.write("ip link add {} type veth peer name {}\n".format(p1, p2))
                file.write("ifconfig {} 192.168.66.{} up\n".format(p2, sw+1))
                file.write("route add default dev {}\n".format(p2))
                file.write("ip link set dev {} up\n".format(p1))
                file.write("ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}\n".\
                    format(sw, p1, p1, sw+2000))
                file.write("ovs-ofctl add-flow s{} \"cookie=0,priority=1 action=drop\"\n"\
                    .format(sw))
                file.write("ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.66.{} action=output:{}\"\n"\
                    .format(sw, sw+1, sw+2000))
                file.write("ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.66.{} action=output:{}\"\n"\
                    .format(sw, sw+1, sw+2000))
                for adj_sw in data[sw]:
                    p = "s{}-s{}".format(sw, adj_sw)
                    if (sw, adj_sw, data[sw][adj_sw]) not in links_set and \
                        (adj_sw, sw, data[sw][adj_sw]) not in links_set:
                        links_set.add((sw, adj_sw, data[sw][adj_sw]))
                    file.write("ip link set dev {} up\n".format(p))
                    file.write("ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}\n"\
                        .format(sw, p, p, adj_sw+1000))
                    file.write("tc qdisc add dev {} root handle 5:0 hfsc default 1\n".format(p))
                    file.write("tc class add dev {} parent 5:0 classid 5:1 hfsc sc rate {}Mbit ul rate {}Mbit\n"\
                        .format(p,500,500))
                    file.write("tc qdisc add dev {} parent 5:1 handle 10: netem delay {}ms\n".format(p,int(data[sw][adj_sw]*1000)))
            os.system("sudo docker cp {}/sw_shell/sw{}_link_init.sh $(sudo docker ps -aqf\"name=^s{}$\"):/home"\
                    .format(self.filePath,sw,sw))
        with open(self.filePath + "/sw_shell/link_init.sh", 'w+') as file:
            for sw in data:
                file.write("sudo docker start s{} > /dev/null\n".format(sw))
            for link in links_set:
                p1 = "s{}-s{}".format(link[0],link[1])
                p2 = "s{}-s{}".format(link[1],link[0])
                # file.write("echo \"s{}连接s{}\"\n".format(link[0],link[1]))
                file.write("sudo ip link add {} type veth peer name {}\n".format(p1, p2))
                # file.write("ovspid1=$(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n".format(link[0]))
                # file.write("ovspid2=$(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n".format(link[1]))
                file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n"
                    .format(p1, p1, link[0]))
                file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n"\
                    .format(p2, p2, link[1]))
                # file.write("sudo docker exec -it s{} ip link set dev {} up\n".format(link[0], p1))
                # file.write("sudo docker exec -it s{} ip link set dev {} up\n".format(link[1], p2))

        with ThreadPoolExecutor(max_workers=len(self.diff_data[0])) as pool:
            all_task = []
            for slot_no in range(self.slot_num):
                all_task.clear()
                for sw in self.diff_data[slot_no]:  # ovs需要删除或者修改的
                    all_task.append(pool.submit(swslot.__config_a_sw_del_change_links, \
                        sw, self.diff_data[slot_no][sw], self.filePath + "/sw_shell/s{}_change_dc_slot{}.sh".format(sw,slot_no)))
                wait(all_task, return_when=ALL_COMPLETED)

                all_task.clear()
                for sw in self.diff_data[slot_no]:  # ovs需要添加的端口
                    all_task.append(pool.submit(swslot.__config_a_sw_add_links, \
                        sw, self.diff_data[slot_no][sw], self.filePath + "/sw_shell/s{}_change_add_slot{}.sh".format(sw,slot_no)))
                wait(all_task, return_when=ALL_COMPLETED)

            all_task.clear()
            for slot_no in range(self.slot_num):    # topo需要添加的链路
                all_task.append(pool.submit(swslot.__config_a_slot_links, \
                    self.diff_data[slot_no], self.filePath + "/sw_shell/change_links_slot{}.sh".format(slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)

                
    @staticmethod
    def __config_a_sw_del_change_links(sw, dlist:list, filename:str):
        with open(filename, 'w+') as file:
            file.write("\n")
            for link in dlist:
                p = "s{}-s{}".format(link[1],link[2])
                if link[0] ==  0:
                    file.write("tc qdisc change dev {} parent 5:1 handle 10: netem delay {}ms\n".\
                        format(p,int(link[3]*1000)))
                elif link[0] == -1:
                    file.write("ovs-vsctl del-port s{} {}\n".format(link[1], p))
                    if link[1]>link[2]:
                        # file.write("echo deletelink\n")
                        file.write("tc qdisc del dev {} root\n".format(p))
                        file.write("ip link delete {} > /dev/null\n".format(p))
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home".format(filename,sw))
    
    @staticmethod
    def __config_a_slot_links(data:dict, filename:str):
        with open(filename, 'w+') as file:
            file.write("\n")
            links_set = set()
            for sw in data:
                for rt in data[sw]:
                    if rt[0] == 0: continue
                    if (rt[0], sw, rt[2]) not in links_set and \
                        (rt[0], rt[2], sw) not in links_set:
                        links_set.add((rt[0], sw, rt[2]))
            for link in links_set:
                p1 = "s{}-s{}".format(link[1],link[2])
                p2 = "s{}-s{}".format(link[2],link[1])
                if link[0] == 1:
                    file.write("sudo ip link add {} type veth peer name {}\n".format(p1, p2))
                    # file.write("ovspid1=$(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n".format(link[1]))
                    # file.write("ovspid2=$(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n".format(link[2]))
                    # file.write("sudo ip link set dev {} name {} netns ${{ovspid1}}\n".format(p1, p1))
                    # file.write("sudo ip link set dev {} name {} netns ${{ovspid2}}\n".format(p2, p2))
                    file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n"
                        .format(p1, p1, link[1]))
                    file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{})\n"\
                        .format(p2, p2, link[2]))
                    # file.write("sudo docker exec -it s{} ip link set dev {} up\n".format(link[1], p1))
                    # file.write("sudo docker exec -it s{} ip link set dev {} up\n".format(link[2], p2))

    @staticmethod
    def __config_a_sw_add_links(sw, dlist:list, filename:str):
        with open(filename, 'w+') as file:
            file.write("\n")
            for link in dlist:
                p = "s{}-s{}".format(link[1],link[2])
                if link[0] ==  1:
                    file.write("ip link set dev {} up\n".format(p))
                    file.write("ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}\n"\
                        .format(link[1], p, p, link[2]+1000))
                    file.write("tc qdisc add dev {} root handle 5:0 hfsc default 1\n".format(p))
                    file.write("tc class add dev {} parent 5:0 classid 5:1 hfsc sc rate {}Mbit ul rate {}Mbit\n"\
                        .format(p,500,500))
                    file.write("tc qdisc add dev {} parent 5:1 handle 10: netem delay {}ms\n".format(p,int(link[3]*1000)))
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home".format(filename,sw))

    @staticmethod
    def __a_sw_links_init(sw):
        # 初始化一个交换机的端口
        os.system("sudo docker exec -it s{} chmod +x /home/sw{}_link_init.sh;\
            sudo docker exec -it s{} /bin/bash /home/sw{}_link_init.sh".format(sw,sw,sw,sw))

    def sw_links_init(self):
        # 加载初始化拓扑
        os.system("sudo chmod +x {path}/sw_shell/link_init.sh;\
            sudo /bin/bash {path}/sw_shell/link_init.sh > /dev/null".format(path=self.filePath))
        with ThreadPoolExecutor(max_workers=len(self.data_slot[0])) as pool:
            all_task = []
            for sw in self.data_slot[0]:
                all_task.append(pool.submit(swslot.__a_sw_links_init, sw))
            wait(all_task, return_when=ALL_COMPLETED)

    @staticmethod
    def __a_sw_links_change_dc(sw, slot_no):
        os.system("sudo docker exec -it s{} chmod +x /home/s{}_change_dc_slot{}.sh;\
            sudo docker exec -it s{} /bin/bash /home/s{}_change_dc_slot{}.sh".format(sw,sw,slot_no,sw,sw,slot_no))

    @staticmethod
    def __a_sw_links_change_add(sw, slot_no):
        # print("sudo docker exec -it s{} chmod +x /home/s{}_change_add_slot{}.sh;\
        #     sudo docker exec -it s{} /bin/bash /home/s{}_change_add_slot{}.sh".format(sw,sw,slot_no,sw,sw,slot_no))
        os.system("sudo docker exec -it s{} chmod +x /home/s{}_change_add_slot{}.sh;\
            sudo docker exec -it s{} /bin/bash /home/s{}_change_add_slot{}.sh".format(sw,sw,slot_no,sw,sw,slot_no))

    @staticmethod
    def __sw_links_change(filename):
        # print("change_links_slot")
        os.system("sudo chmod +x {filename};\
            sudo /bin/bash {filename}".format(filename=filename))

    @staticmethod
    def sw_links_change(dslot, slot_no):
        # 时间片切换，拓扑切换
        with ThreadPoolExecutor(max_workers=len(dslot.data_slot[0])+1) as pool:
            all_task = []
            # print("links_change_dc")
            for sw in dslot.data_slot[0]:
                all_task.append(pool.submit(swslot.__a_sw_links_change_dc, sw, slot_no))
            all_task.append(pool.submit(swslot.__sw_links_change, "{}/sw_shell/change_links_slot{}.sh".format(dslot.filePath, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            # print("links_change_add")
            for sw in dslot.data_slot[0]:
                all_task.append(pool.submit(swslot.__a_sw_links_change_add, sw, slot_no))
            wait(all_task, return_when=ALL_COMPLETED)


if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    dslot = swslot(filePath + '/timeslot')
    
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