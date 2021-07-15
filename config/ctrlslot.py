import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from topo_ovs.config.swslot import swslot


class ctrlslot:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.ctrl_slot = dict() # 所有时间片的数据
        self.ctrl_slot_add = dict() # 所有时间片的数据
        self.ctrl_slot_del = dict() # 所有时间片的数据
        self.filePath = filePath
        self.start(filePath)
    
    @staticmethod
    def load_ctrl_from_file(filename:str):
        # 从文件当中加载一个时间片的控制器位置信息
        ctrl_num = 0
        with open(file=filename) as file:
            lines = file.read().splitlines()
            ctrl_num = int(lines[0].strip('\n')) # 获取控制器的数量
            del lines[0:1] # 删除前面的一行内容
        data = dict()
        ctrl = lines[::2]       # 控制器所在的卫星交换机的编号
        ctrlsw = lines[1::2]    # 控制器控制的卫星交换机编号
        for index in range(ctrl_num):
            data[int(ctrl[index])] = list(map(int, ctrlsw[index].strip(' ').split(' ')))
        return data

    def start(self, filePath:str):
        self.slot_num = len(os.listdir(filePath + "/ctrl_deploy"))    # 获取时间片个数
        for index in range(self.slot_num):
            self.ctrl_slot[index] = ctrlslot.load_ctrl_from_file(filePath + "/ctrl_deploy/ctrl_" + str(index))
        for index in range(self.slot_num):
            self.ctrl_slot_add[index] = list()
            self.ctrl_slot_del[index] = list()
            next = (index+1)%self.slot_num
            for ctrl in self.ctrl_slot[index]:
                if ctrl not in self.ctrl_slot[next]:
                    self.ctrl_slot_del[index].append(ctrl)
            for ctrl in self.ctrl_slot[next]:
                if ctrl not in self.ctrl_slot[index]:
                    self.ctrl_slot_add[index].append(ctrl)

    # @staticmethod
    # def __load_a_ctrl(sw):
    #     # 建立控制器和交换机的本地连接
    #     p1 = "s{}-c{}".format(sw, sw)
    #     p2 = "c{}-s{}".format(sw, sw) 
    #     os.system("sudo docker start c{sw};\
    #         sudo ip link add {p1} type veth peer name {p2}".format(sw, p1, p2))
    #     os.system("ovspid=$(sudo docker inspect -f '{{{{.State.Pid}}}}' s{sw}); \
    #             ctrlpid=$(sudo docker inspect -f '{{{{.State.Pid}}}}' c{sw}); \
    #             sudo ip link set dev {p1} name {p1} netns ${{ovspid}} \
    #             sudo ip link set dev {p2} name {p2} netns ${{ctrlpid}}"\
    #             .format(sw=sw,p1=p1,p2=p2))
    #     os.system("sudo docker exec -it s{} ip link set dev {} up".format(sw, p1))
    #     os.system("sudo docker exec -it c{} ip link set dev {} up".format(sw, p2))
    #     os.system("sudo docker exec -it c{} ip addr add 192.168.67.{} dev {}".format(sw, sw+1, p2))
    #     os.system("sudo docker exec -it c{} /bin/bash /usr/src/openmul/mul.sh start mycontroller > /dev/null"\
    #         .format(sw))
    #     # 设置控制器的默认路由
    #     os.system("sudo docker exec -it c{} ip route flush table main".format(sw))
    #     os.system("sudo docker exec -it c{} route add default dev {}".format(sw, p2))
    #     # docker中的ovs连接端口
    #     os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null".\
    #         format(sw, sw, p1, p1, 3000+sw))
    #     os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.67.{} action=output:{}\""\
    #         .format(sw, sw, sw+1, sw+3000))
    #     os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.67.{} action=output:{}\""\
    #         .format(sw, sw, sw+1, sw+3000))

    @staticmethod
    def __config2sh_ctrl_add(ctrl, file):
        # 加载一个控制器
        file.write("echo 加载控制器c{}\n".format(ctrl))
        p1 = "s{ctrl}-c{ctrl}".format(ctrl=ctrl)
        p2 = "c{ctrl}-s{ctrl}".format(ctrl=ctrl)
        file.write("sudo docker start c{ctrl} > /dev/null\n".format(ctrl=ctrl))
        file.write("sudo ip link add {p1} type veth peer name {p2}\n".format(p1=p1, p2=p2))
        file.write("sudo ip link set dev {p1} name {p1} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{ctrl})\n"\
            .format(ctrl=ctrl,p1=p1,p2=p2))
        file.write("sudo ip link set dev {p2} name {p2} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' c{ctrl})\n"\
            .format(ctrl=ctrl,p1=p1,p2=p2))
        file.write("sudo docker exec -it s{ctrl} ip link set dev {p1} up\n".format(ctrl=ctrl,p1=p1))
        file.write("sudo docker exec -it c{ctrl} ip link set dev {p2} up\n".format(ctrl=ctrl,p2=p2))
        file.write("sudo docker exec -it c{ctrl} ip addr add 192.168.67.{ctrl_ip} dev {p2}\n".format(ctrl=ctrl,ctrl_ip=ctrl+1, p2=p2))
        # file.write("sudo docker exec -it c{ctrl} /bin/bash /usr/src/openmul/mul.sh start mycontroller > /dev/null\n"\
        #     .format(ctrl=ctrl))
        # 设置控制器的默认路由
        file.write("sudo docker exec -it c{ctrl} ip route flush table main\n".format(ctrl=ctrl))
        file.write("sudo docker exec -it c{ctrl} route add default dev {p2}\n".format(ctrl=ctrl, p2=p2))
        # docker中的ovs连接端口
        file.write("sudo docker exec -it s{ctrl} ovs-vsctl add-port s{ctrl} {p1} -- set interface {p1} ofport_request={ctrl_port} > /dev/null\n".\
            format(ctrl=ctrl, p1=p1, ctrl_port=3000+ctrl))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl add-flow s{ctrl} \"cookie=0,priority=2,ip,nw_dst=192.168.67.{ctrl_ip} action=output:{ctrl_port}\"\n"\
            .format(ctrl=ctrl, ctrl_ip=ctrl+1, ctrl_port=3000+ctrl))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl add-flow s{ctrl} \"cookie=0,priority=2,arp,nw_dst=192.168.67.{ctrl_ip} action=output:{ctrl_port}\"\n" \
            .format(ctrl=ctrl, ctrl_ip=ctrl+1, ctrl_port=3000+ctrl))

    @staticmethod
    def __config2sh_ctrl_del(ctrl, file):
        # 加载一个控制器
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl del-flows s{ctrl} \"ip,nw_dst=192.168.67.{ctrl_ip}\"\n" \
            .format(ctrl=ctrl, ctrl_ip=ctrl+1))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl del-flows s{ctrl} \"arp,nw_dst=192.168.67.{ctrl_ip}\"\n" \
            .format(ctrl=ctrl, ctrl_ip=ctrl+1))
        file.write("sudo docker exec -it s{ctrl} ovs-vsctl del-port s{ctrl} s{ctrl}-c{ctrl}\n".\
            format(ctrl=ctrl))
        file.write("sudo docker exec -it c{ctrl} ip link delete c{ctrl}-s{ctrl}\n".format(ctrl=ctrl))
        # file.write("sudo docker exec -it c{} /bin/bash /usr/src/openmul/mul.sh stop > /dev/null"\
        #     .format(ctrl))
        file.write("sudo docker stop c{}\n".format(ctrl))

    def config2sh(self):
        with open(self.filePath + "/ctrl_shell/ctrl_init.sh", 'w+') as file:
            for ctrl in self.ctrl_slot[0]:
                ctrlslot.__config2sh_ctrl_add(ctrl,file)
            # for ctrl in self.ctrl_slot_add[0]:
            #     ctrlslot.__config2sh_ctrl_add(ctrl,file)
        for slot_no in self.ctrl_slot_add:
            with open(self.filePath + "/ctrl_shell/ctrl_add_slot{}.sh".format(slot_no), 'w+') as file:
                for ctrl in self.ctrl_slot_add[slot_no]:
                    ctrlslot.__config2sh_ctrl_add(ctrl,file)
            with open(self.filePath + "/ctrl_shell/ctrl_del_slot{}.sh".format(slot_no), 'w+') as file:
                for ctrl in self.ctrl_slot_del[slot_no]:
                    ctrlslot.__config2sh_ctrl_del(ctrl,file)

    @staticmethod
    def __run_ctrl_shell(filename):
        os.system("sudo chmod +x {};sudo /bin/bash {}".format(filename, filename))

    def ctrl_init(self):
        ctrlslot.__run_ctrl_shell(self.filePath + "/ctrl_shell/ctrl_init.sh")
    
    @staticmethod
    def ctrl_change_add(cslot:swslot, slot_no):
        ctrlslot.__run_ctrl_shell(cslot.filePath + "/ctrl_shell/ctrl_add_slot{}.sh".format(slot_no))
    
    @staticmethod
    def ctrl_change_del(cslot:swslot, slot_no):
        ctrlslot.__run_ctrl_shell(cslot.filePath + "/ctrl_shell/ctrl_del_slot{}.sh".format(slot_no))


if __name__ == "__main__":
    filePath = os.path.dirname(__file__)
    dslot = ctrlslot(filePath)
    count_all = 0
    for index in dslot.ctrl_slot:
        tmp = 0
        print("第{}个时间片:".format(index))
        for ctrl in dslot.ctrl_slot[index]:
            tmp0 = len(dslot.ctrl_slot[index][ctrl])
            print("控制器{}控制{}个卫星交换机".format(ctrl, tmp0))
            tmp += tmp0
        print(tmp)
        count_all += tmp
    print(count_all)