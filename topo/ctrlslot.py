import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

class ctrlslot:
    def __init__(self, filePath:str) -> None:
        self.slot_num = 0   # 时间片的个数
        self.ctrl_slot = dict() # 所有时间片的数据，每一个时间片的控制器
        self.ctrl_slot_standby = dict() # 所有时间片的数据，备用控制器
        self.ctrl_slot_add = dict() # 所有时间片的数据，每一个时间片切换需要添加的控制器
        self.ctrl_slot_del = dict() # 所有时间片的数据，每一个时间片切换需要删除的控制器
        self.ctrl_slot_stay = dict()    # 所有时间片的数据，每一个时间片切换需要保留的控制器
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
                data[int(ctrl[index])] = list(map(int, ctrlsw[index].strip().split(' ')))
        return data

    def start(self, filePath:str):
        self.slot_num = len(os.listdir(filePath + "/ctrl_deploy"))    # 获取时间片个数
        for index in range(self.slot_num):
            self.ctrl_slot[index] = ctrlslot.load_ctrl_from_file(filePath + "/ctrl_deploy/ctrl_" + str(index))
        for index in range(self.slot_num):
            self.ctrl_slot_add[index] = list()
            self.ctrl_slot_del[index] = list()
            self.ctrl_slot_stay[index] = list()
            next = (index+1)%self.slot_num
            for ctrl in self.ctrl_slot[index]:
                if ctrl not in self.ctrl_slot[next]:
                    self.ctrl_slot_del[index].append(ctrl)
                else:
                    self.ctrl_slot_stay[index].append(ctrl)
            for ctrl in self.ctrl_slot[next]:
                if ctrl not in self.ctrl_slot[index]:
                    self.ctrl_slot_add[index].append(ctrl)
        for index in range(self.slot_num):
            with open(file=filePath + "/standby/standby_ctrl_{}".format(index)) as file:
                lines = file.read().splitlines()
                # sw_num = int(lines[0].strip('\n')) # 交换机的数量
                # del lines[0:1] # 删除前面的一行内容
                self.ctrl_slot_standby[index] = list(map(int, lines[1].strip().split())) 
        self.sw2ctrl = dict()
        self.sw2ctrl_standby = self.ctrl_slot_standby
        for slot_no in self.ctrl_slot_add:
            self.sw2ctrl[slot_no] = dict()
            for ctrl_no in self.ctrl_slot[slot_no]:
                for sw_no in self.ctrl_slot[slot_no][ctrl_no]:
                    self.sw2ctrl[slot_no][sw_no] = ctrl_no

    @staticmethod
    def __config2sh_ctrl_add(ctrl, file):
        # 加载一个控制器
        # file.write("echo 加载控制器c{}\n".format(ctrl))
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
        file.write("sudo docker exec -it c{ctrl} ifconfig {p2} 192.168.67.{ctrl_ip} netmask 255.255.0.0 up\n".format(ctrl=ctrl, ctrl_ip=ctrl+1, p2=p2))
        # 设置控制器的默认路由
        file.write("sudo docker exec -it c{ctrl} ip route flush table main\n".format(ctrl=ctrl))
        file.write("sudo docker exec -it c{ctrl} route add default dev {p2}\n".format(ctrl=ctrl, p2=p2))
        # docker中的ovs连接端口
        file.write("sudo docker exec -it s{ctrl} ovs-vsctl add-port s{ctrl} {p1} -- set interface {p1} ofport_request={ctrl_port} > /dev/null\n".\
            format(ctrl=ctrl, p1=p1, ctrl_port=3000+ctrl))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl add-flow s{ctrl} \"cookie=0,idle_timeout=65535,priority=20,ip,nw_dst=192.168.67.{ctrl_ip} action=output:{ctrl_port}\"\n"\
            .format(ctrl=ctrl, ctrl_ip=ctrl+1, ctrl_port=3000+ctrl))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl add-flow s{ctrl} \"cookie=0,idle_timeout=65535,priority=20,arp,nw_dst=192.168.67.{ctrl_ip} action=output:{ctrl_port}\"\n" \
            .format(ctrl=ctrl, ctrl_ip=ctrl+1, ctrl_port=3000+ctrl))
        file.write("sudo docker exec -it c{ctrl} /bin/bash /home/openmul/mul.sh init\n"\
            .format(ctrl=ctrl))
        file.write("sudo docker exec -it c{ctrl} /bin/bash /home/openmul/mul.sh start mulhello\n"\
            .format(ctrl=ctrl))

    @staticmethod
    def __config2sh_ctrl_del(ctrl, file):
        # 删除一个控制器
        file.write("sudo docker exec -it c{} /bin/bash /home/openmul/mul.sh stop\n"\
            .format(ctrl))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl del-flows s{ctrl} \"ip,nw_dst=192.168.67.{ctrl_ip}\"\n" \
            .format(ctrl=ctrl, ctrl_ip=ctrl+1))
        file.write("sudo docker exec -it s{ctrl} ovs-ofctl del-flows s{ctrl} \"arp,nw_dst=192.168.67.{ctrl_ip}\"\n" \
            .format(ctrl=ctrl, ctrl_ip=ctrl+1))
        file.write("sudo docker exec -it s{ctrl} ovs-vsctl del-port s{ctrl} s{ctrl}-c{ctrl}\n".\
            format(ctrl=ctrl))
        file.write("sudo docker exec -it c{ctrl} ip link delete c{ctrl}-s{ctrl}\n".format(ctrl=ctrl))
        file.write("sudo docker stop c{}\n".format(ctrl))

    def config2sh(self):
        with open(self.filePath + "/ctrl_shell/ctrl_init.sh", 'w+') as file:
            for ctrl in self.ctrl_slot[0]:
                file.write("sudo docker cp {}/ctrl_connect/slot_0_ctrl_{} $(sudo docker ps -aqf\"name=^c{}$\"):/home/ctrl_connect\n"\
                    .format(self.filePath,ctrl,ctrl))
                ctrlslot.__config2sh_ctrl_add(ctrl,file)
        for slot_no in self.ctrl_slot_add:
            with open(self.filePath + "/ctrl_shell/ctrl_add_slot{}.sh".format(slot_no), 'w+') as file:
                for ctrl in self.ctrl_slot[(slot_no+1)%len(self.ctrl_slot_add)]:
                    file.write("sudo docker cp {}/ctrl_connect/slot_{}_ctrl_{} $(sudo docker ps -aqf\"name=^c{}$\"):/home/ctrl_connect\n"\
                        .format(self.filePath,(slot_no+1)%len(self.ctrl_slot_add),ctrl,ctrl))
                for ctrl in self.ctrl_slot_add[slot_no]:
                    ctrlslot.__config2sh_ctrl_add(ctrl,file)
            with open(self.filePath + "/ctrl_shell/ctrl_del_slot{}.sh".format(slot_no), 'w+') as file:
                for ctrl in self.ctrl_slot_del[slot_no]:
                    ctrlslot.__config2sh_ctrl_del(ctrl,file)
            # with open(self.filePath + "/ctrl_shell/ctrl_restart_slot{}.sh".format(slot_no), 'w+') as file:
            #     for ctrl in self.ctrl_slot[slot_no]:
            #         if ctrl not in self.ctrl_slot_add[slot_no] and ctrl not in self.ctrl_slot_del[slot_no]:
            #             file.write("sudo docker exec c{} echo {} > /dev/udp/127.0.0.1/12000\n".format(ctrl, slot_no))
                        # file.write("sudo docker exec -it c{} /bin/bash /home/openmul/mul.sh stop\n"\
                        #     .format(ctrl))
                        # file.write("sudo docker exec -it c{} /bin/bash /home/openmul/mul.sh start mulhello\n"\
                        #     .format(ctrl))            
        #     datactrl = self.ctrl_slot[slot_no]
        #     for ctrl_no in datactrl:
        #         for sw in datactrl[ctrl_no]:
        #             with open(self.filePath + "/standby_file/sw{}_standby_slot{}.sh".format(sw, slot_no), 'w+') as file:
        #                 ctrl_no_standby = self.ctrl_slot_standby[slot_no][sw]
        #                 file.write("ping -c3 -i0.2 -W1 192.168.67.{}  &> /dev/null\n".format(ctrl_no+1))
        #                 file.write("if [ $? -eq 0 ];then \novs-vsctl set-controller s{sw} tcp:192.168.67.{ctrl_master}:6653 -- set bridge s{sw} other_config:enable-flush=false\nelse \novs-vsctl set-controller s{sw} tcp:192.168.67.{ctrl_standby}:6653 -- set bridge s{sw} other_config:enable-flush=false \nfi\n"
        #                     .format(sw=sw, ctrl_master=ctrl_no+1,ctrl_standby=ctrl_no_standby+1))
        #             # os.system("sudo docker cp {}/standby_file/sw{}_standby_slot{}.sh $(sudo docker ps -aqf\"name=^s{}$\"):/home\n"\
        #             #     .format(self.filePath,sw,slot_no,sw))
        #                 # file.write("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}:6653 -- set bridge s{} other_config:enable-flush=false,fail-mode=secure\n"\
        #                 #         .format(sw, sw, ctrl_no+1, sw))
        # for slot_no in self.ctrl_slot_add:
        #     with ThreadPoolExecutor(max_workers=len(self.ctrl_slot_standby[slot_no])) as pool:
        #         all_task = []
        #         for sw in range(len(self.ctrl_slot_standby[slot_no])):
        #             all_task.append(pool.submit(ctrlslot.docker_cp, sw, "{}/standby_file/sw{}_standby_slot{}.sh".format(self.filePath,sw,slot_no)))
        #         wait(all_task, return_when=ALL_COMPLETED)

        # 所有交换机所有时间片连接的控制器文件生成
        # for sw in range(len(self.ctrl_slot_standby[slot_no])):
        #     with open(self.filePath + "/standby_file/s{}_ctrl_file".format(sw), 'w+') as file:
        #         for slot_no in self.sw2ctrl:
        #             file.write("{} ".format(self.sw2ctrl[slot_no][sw]))
        #         file.write("\n")
        #         for slot_no in self.sw2ctrl_standby:
        #             file.write("{} ".format(self.sw2ctrl_standby[slot_no][sw]))
        # with ThreadPoolExecutor(max_workers=len(self.ctrl_slot_standby[slot_no])) as pool:
        #     all_task = []
        #     for sw in sw2ctrl[0]:
        #         all_task.append(pool.submit(ctrlslot.docker_cp, sw, "{}/standby_file/s{}_ctrl_file".format(self.filePath,sw)))
        #     wait(all_task, return_when=ALL_COMPLETED)

    @staticmethod
    def docker_cp(sw, filename):
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home\n".format(filename,sw))

    @staticmethod
    def __run_ctrl_shell(filename):
        os.system("sudo chmod +x {};sudo /bin/bash {} > /dev/null".format(filename, filename))

    def ctrl_init(self):
        ctrlslot.__run_ctrl_shell(self.filePath + "/ctrl_shell/ctrl_init.sh")
    
    @staticmethod
    def ctrl_change_add(cslot, slot_no):
        ctrlslot.__run_ctrl_shell(cslot.filePath + "/ctrl_shell/ctrl_add_slot{}.sh".format(slot_no))
    
    @staticmethod
    def ctrl_change_del(cslot, slot_no):
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