import os


class topobuilder:
    sw_set = set()  # 保存sw的dpid
    ctrl_set = set()    # 保存目前在运行的控制器
    db_set = set()
    veth_set = set()    # 使用veth-pair来构建链路，同时使用tc流量控制来设置时延和带宽等

    @staticmethod
    def change_slot_sw(swslot:dict):
        # 时间片切换，更改卫星交换机的连接
        for sw in swslot:
            if sw in sw_dr.sw_disable_set: continue     # 失效的卫星交换机
            for command in swslot[sw]:
                if command[1] in sw_dr.sw_disable_set: continue
                p1 = "s{}-s{}".format(sw, command[1])
                p2 = "s{}-s{}".format(command[1], sw)
                if(command[0] == 0):    # 改变链路的时延距离
                    topobuilder.change_tc(p1, command[2]*1000)
                    topobuilder.change_tc(p2, command[2]*1000)
                elif(command[0] == -1):     # 删除链路
                    if((p1, p2) in topobuilder.veth_set):
                        topobuilder.del_veth(p1, p2)
                        os.system("sudo docker exec -it s{} ovs-vsctl del-port s{} {}".format(sw, sw, p1))
                        os.system("sudo docker exec -it s{} ovs-vsctl del-port s{} {}".format(command[1], command[1], p2))
                    elif((p2, p1) in topobuilder.veth_set):
                        topobuilder.del_veth(p2, p1)
                        os.system("sudo docker exec -it s{} ovs-vsctl del-port s{} {}".format(sw, sw, p1))
                        os.system("sudo docker exec -it s{} ovs-vsctl del-port s{} {}".format(command[1], command[1], p2))
                elif(command[0] == 1):  # 添加链路
                    if(((p1, p2) not in topobuilder.veth_set) and ((p2, p1) not in topobuilder.veth_set)):
                        topobuilder.add_veth(p1, p2, command[2]*1000)
                        topobuilder.load_sw_link(sw, command[1])

    @staticmethod
    def change_slot_ctrl(cslot_b:dict, cslot_n:dict):
        # 时间片切换，更改控制器的连接
        # 先关闭旧的控制器，再打开新的控制器
        for ctrl in cslot_b:
            if ctrl not in cslot_n:
                os.system("sudo docker exec -it c{} ip link delete c{}-s{}".format(ctrl, ctrl, ctrl))
                os.system("sudo docker stop c{}".format(ctrl))
                topobuilder.ctrl_set.remove(ctrl)
        for ctrl in cslot_n:
            if ctrl not in topobuilder.ctrl_set:
                topobuilder.ctrl_set.add(ctrl)
                os.system("sudo docker start c{} > /dev/null".format(ctrl))  # 启动docker
                topobuilder.load_ctrl_link(ctrl)
            for sw in cslot_n[ctrl]:
                if sw not in cslot_b[ctrl] and sw not in sw_dr.sw_disable_set:
                    os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}".format(sw, sw, ctrl))

    @staticmethod
    def load_slot(dataslot:dict):
        # load a time slot topo 加载一个时间片拓扑
        # 添加交换机
        print("加载卫星交换机")
        for sw in range(len(dataslot)):
            topobuilder.add_ovs_switch(sw)

        # 添加卫星交换机之间的连接
        for sw in dataslot:
            print("加载卫星交换机{}和相邻的卫星交换机之间的连接".format(sw))
            for adj_sw in dataslot[sw]:
                topobuilder.load_sw_link(sw, adj_sw, dataslot[sw][adj_sw])

    @staticmethod
    def load_ctrl(datactrl:dict):
        # 加载一个时间片的控制器
        for ctrl in datactrl:
            print("加载控制器{}以及设置其控制的卫星交换机".format(ctrl))
            topobuilder.ctrl_set.add(ctrl)
            os.system("sudo docker start c{} > /dev/null".format(ctrl))  # 启动docker
            topobuilder.load_ctrl_link(ctrl)

    @staticmethod
    def load_db(dbdata:list):
        # 加载分布式数据库
        for db in dbdata:
            print("加载分布式数据库{}".format(db))
            topobuilder.db_set.add(db)
            os.system("sudo docker start db{} > /dev/null".format(db))  # 启动docker
            topobuilder.load_db_link(db)
    
    @staticmethod
    def del_slot() -> None:
        # 删除一个时间片拓扑，清空
        for p in topobuilder.veth_set:
            topobuilder.del_veth(p[0], p[1])
        for s in topobuilder.sw_set:
            topobuilder.del_ovs_switch(s)
        for ctrl in topobuilder.ctrl_set:
            os.system("sudo docker exec -it c{} ip link delete c{}-s{}".format(ctrl, ctrl, ctrl))
            os.system("sudo docker exec -it c{} /bin/bash /usr/src/openmul/mul.sh stop > /dev/null"\
                .format(ctrl))
            os.system("sudo docker stop c{}".format(ctrl))
        for db in topobuilder.db_set:
            os.system("sudo docker exec -it db{} ip link delete db{}-s{}".format(db, db, db))
            os.system("sudo docker stop db{}".format(db))
        topobuilder.db_set.clear()
        topobuilder.ctrl_set.clear()
        topobuilder.sw_set.clear()
        topobuilder.veth_set.clear()
    
    @staticmethod
    def del_tc(interface: str):
        # delete the tc set 删除vnet上的tc设置
        os.system("sudo tc qdisc del dev {} root".format(interface))

    @staticmethod
    def add_tc(interface: str, delay=None, bandwidth=None, loss=None):
        # set the tc of interface 在接口上设置tc
        if delay is None and bandwidth is None and loss is None:
            return
        # use hfsc queue
        if bandwidth is not None:
            os.system(
                "sudo tc qdisc add dev {} root handle 5:0 hfsc default 1".format(interface))
            os.system(
                "sudo tc class add dev {} parent 5:0 classid 5:1 hfsc sc rate {}Mbit ul rate {}Mbit".format(
                    interface,
                    bandwidth,
                    bandwidth)
            )

        if delay is None and loss is None:
            return
        # delay and loss
        delay_loss = "sudo tc qdisc add dev {} parent 5:1 handle 10: netem".format(
            interface)
        if delay is not None:
            delay_loss += " delay {}ms".format(delay)
        if loss is not None and int(loss) != 0:
            delay_loss += " loss {}".format(loss)
        os.system(delay_loss)

    @staticmethod
    def change_tc(interface: str, delay=None, bandwidth=None, loss=None):
        # 改变对应端口的tc设置
        if delay is None and bandwidth is None and loss is None:
            return
        # use hfsc
        if bandwidth is not None:
            os.system(
                "sudo tc class change dev {} parent 5:0 classid 5:1 hfsc sc rate {}Mbit ul rate {}Mbit".format(
                    interface,
                    bandwidth,
                    bandwidth)
            )

        if delay is None and loss is None:
            return

        # delay and loss
        delay_loss = "sudo tc qdisc change dev {} parent 5:1 handle 10: netem".format(
            interface)
        if delay is not None:
            delay_loss += " delay {}ms".format(delay)
        if loss is not None and int(loss) != 0:
            delay_loss += " loss {}".format(loss)
        os.system(delay_loss)

    @staticmethod
    def add_veth(p1, p2, delay):
        # add a pair of veth 添加一个veth对
        os.system("sudo ip link add {} type veth peer name {}".format(p1, p2))
        topobuilder.veth_set.add((p1, p2))
        topobuilder.add_tc(p1, delay, 1000)
        topobuilder.add_tc(p2, delay, 1000)
        # os.system("echo \"add a links between {} done\"".format(p1))

    @staticmethod
    def del_veth(p1, p2):
        # delete a pair of veth(only need to delete one, another one will auto delete)删除一个veth对
        topobuilder.del_tc(p1)
        topobuilder.del_tc(p2)
        os.system("sudo ip link delete {} > /dev/null".format(p1))
        os.system("sudo ip link delete {} > /dev/null".format(p2))
        # os.system("echo \"delete a links between {} done\"".format(p1))

    @staticmethod
    def load_sw_link(sw1, sw2, delay):
        # 建立交换机之间的连接
        p1 = "s{}-s{}".format(sw1, sw2)
        p2 = "s{}-s{}".format(sw2, sw1)
        if(((p1, p2) in topobuilder.veth_set) or ((p2, p1) in topobuilder.veth_set)):return
        topobuilder.add_veth(p1, p2, delay*1000)
        ovspid1 = read_pid("s{}".format(sw1))
        ovspid2 = read_pid("s{}".format(sw2))
        # print("sudo ip link set dev {} name {} netns {}".format(p1, p1, ovspid1))
        os.system("sudo ip link set dev {} name {} netns {}".format(p1, p1, ovspid1))
        os.system("sudo ip link set dev {} name {} netns {}".format(p2, p2, ovspid2))
        os.system("sudo docker exec -it s{} ip link set dev {} up".format(sw1, p1))
        os.system("sudo docker exec -it s{} ip link set dev {} up".format(sw2, p2))
        os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}"\
            .format(sw1, sw1, p1, p1, sw2+1000))
        os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}"\
            .format(sw2, sw2, p2, p2, sw1+1000))
    
    @staticmethod
    def load_ctrl_link(sw):
        # 建立控制器和交换机的本地连接
        p1 = "s{}-c{}".format(sw, sw)
        p2 = "c{}-s{}".format(sw, sw) 
        topobuilder.add_veth(p1, p2, 0) # 添加链路和端口
        ovspid = read_pid("s{}".format(sw))
        ctrlpid = read_pid("c{}".format(sw))
        os.system("sudo ip link set dev {} name {} netns {}".format(p1, p1, ovspid))
        os.system("sudo ip link set dev {} name {} netns {}".format(p2, p2, ctrlpid))
        os.system("sudo docker exec -it s{} ip link set dev {} up".format(sw, p1))
        os.system("sudo docker exec -it c{} ip link set dev {} up".format(sw, p2))
        os.system("sudo docker exec -it c{} ip addr add 192.168.67.{} dev {}".format(sw, sw+1, p2))
        os.system("sudo docker exec -it c{} /bin/bash /usr/src/openmul/mul.sh start mycontroller > /dev/null"\
            .format(sw))
        # 设置控制器的默认路由
        os.system("sudo docker exec -it c{} ip route flush table main".format(sw))
        os.system("sudo docker exec -it c{} route add default dev {}".format(sw, p2))
        # docker中的ovs连接端口
        os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null".\
            format(sw, sw, p1, p1, 3000+sw))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.67.{} action=output:{}\""\
            .format(sw, sw, sw+1, sw+3000))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.67.{} action=output:{}\""\
            .format(sw, sw, sw+1, sw+3000))
    
    @staticmethod
    def load_db_link(sw):
        # 建立数据库和交换机之间的链路
        p1 = "s{}-db{}".format(sw, sw)
        p2 = "db{}-s{}".format(sw, sw) 
        topobuilder.add_veth(p1, p2, 0) # 添加链路和端口
        ovspid = read_pid("s{}".format(sw))
        dbpid = read_pid("db{}".format(sw))
        os.system("sudo ip link set dev {} name {} netns {}".format(p1, p1, ovspid))
        os.system("sudo ip link set dev {} name {} netns {}".format(p2, p2, dbpid))
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

    @staticmethod
    def add_ovs_switch(switch_id):
        # add a switch into net 添加一个ovs交换机，使用docker
        # docker run -it --name=s1 --net=none noiro/openvswitch:5.2.1.0.a444194 /bin/bash
        os.system("sudo docker start s{}".format(switch_id))
        os.system("sudo docker exec -it s{} /bin/bash /home/ovs_open.sh > /dev/null".format(switch_id))
        os.system("sudo docker exec -it s{} ovs-vsctl add-br s{} -- set bridge s{} protocols=OpenFlow10,OpenFlow11,OpenFlow12,OpenFlow13 other-config:datapath-id={}".format(
                switch_id, switch_id, switch_id, switch_id))
        # 添加本地端口和默认路由
        p1 = "s{}-h{}".format(switch_id, switch_id)
        p2 = "h{}-s{}".format(switch_id, switch_id)
        os.system("sudo docker exec -it s{} ip link add {} type veth peer name {}".format(switch_id, p1, p2))
        os.system("sudo docker exec -it s{} ifconfig {} 192.168.66.{} up".format(switch_id, p2, switch_id+1))
        os.system("sudo docker exec -it s{} route add default dev {}".format(switch_id, p2))
        os.system("sudo docker exec -it s{} ip link set dev {} up".format(switch_id, p1))
        os.system("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}".\
            format(switch_id, switch_id, p1, p1, switch_id+2000))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,ip,nw_dst=192.168.66.{} action=output:{}\""\
            .format(switch_id, switch_id, switch_id+1, switch_id+2000))
        os.system("sudo docker exec -it s{} ovs-ofctl add-flow s{} \"cookie=0,priority=2,arp,nw_dst=192.168.66.{} action=output:{}\""\
            .format(switch_id, switch_id, switch_id+1, switch_id+2000))
        topobuilder.sw_set.add(switch_id)
        # os.system("echo \"add a switch s{} done\"".format(switch_id))

    @staticmethod
    def del_ovs_switch(switch_id):
        # delete a switch from net 删除一个ovs交换机
        os.system("sudo docker exec -it s{} ovs-vsctl del-br s{} > /dev/null".format(switch_id, switch_id))
        os.system("sudo docker exec -it s{} ip link delete h{}-s{}".format(switch_id, switch_id, switch_id))
        os.system("sudo docker stop s{}".format(switch_id))
        topobuilder.sw_set.remove(switch_id)
        # os.system("echo \"delete a switch s{} done\"".format(switch_id))


def read_pid(docker_name:str):
    # 从系统中读取容器的网络命名空间id，并返回
    os.system("echo $(sudo docker inspect -f '{{{{.State.Pid}}}}' {}) > {}"\
        .format(docker_name,docker_name))
    with open(docker_name) as file:
        line = file.readline().strip()
        pid = int(line)
        os.system("rm {}".format(docker_name))
        return pid

class sw_dr:
    # 卫星交换机的容灾
    sw_disable_set = set()  # 实效的卫星交换机

    @staticmethod
    def disable_sw(sw, swslot:dict, cslot:dict):
        # 使sw失效
        sw_dr.sw_disable_set.add(sw)
        # 先删除与交换机的链路
        for adj_sw in swslot[sw]:
            p1 = "s{}-s{}".format(sw, adj_sw)
            p2 = "s{}-s{}".format(adj_sw, sw)
            if((p1, p2) in topobuilder.veth_set):
                topobuilder.del_veth(p1, p2)
            elif((p2, p1) in topobuilder.veth_set):
                topobuilder.del_veth(p2, p1)
        # 删除与本地连接的控制器
        if sw in cslot:
            p1 = "s{}-c{}".format(sw, sw)
            p2 = "c{}-s{}".format(sw, sw)
            os.system("sudo docker exec -it s{} ip link delete {} ".format(sw, p1))
            topobuilder.del_veth(p1, p2)
        # 再删除交换机
        topobuilder.del_ovs_switch(sw)
    
    @staticmethod
    def enable_sw(sw, swslot:dict, cslot:dict):
        # 使能sw
        sw_dr.sw_disable_set.remove(sw)
        topobuilder.add_ovs_switch(sw)
        # 添加交换机的链路
        for adj_sw in swslot[sw]:
            topobuilder.load_sw_link(sw, adj_sw, swslot[sw][adj_sw])

        # 连接控制器
        if sw in cslot:
            topobuilder.load_ctrl_link(sw)
        for ctrl in cslot:
            if sw in cslot[ctrl]:
                os.system("sudo docker exec -it s{} ovs-vsctl set-controller s{} tcp:192.168.67.{}".format(sw, sw, ctrl))
                return