import os
from typing import Dict, Set
from namespace.nsbuilder import nsbuilder

class topobulider:
    sw_set = Set()  # 保存sw的dpid
    veth_set = Set()    # 使用veth-pair来构建链路，同时使用tc流量控制来设置时延和带宽等

    @staticmethod
    def change_slot_sw(cslot:Dict):
        for sw in cslot:
            for command in cslot[sw]:
                p1 = "s{}-s{}".format(sw, command[1])
                p2 = "s{}-s{}".format(command[1], sw)
                if(command[0] == 0):
                    topobulider.change_tc(p1, command[2]*1000, 10)
                    topobulider.change_tc(p2, command[2]*1000, 10)
                elif(command[0] == -1):
                    if((p1, p2) in topobulider.veth_set):
                        topobulider.del_veth(p1, p2)
                    elif((p2, p1) in topobulider.veth_set):
                        topobulider.del_veth(p1, p2)
                elif(command[0] == 1):
                    if(((p1, p2) not in topobulider.veth_set) and ((p2, p1) not in topobulider.veth_set)):
                        topobulider.add_veth(p1, p2, command[2]*1000)

    @staticmethod
    def load_slot(dataslot:Dict):
        # load a time slot topo 加载一个时间片拓扑
        nsbuilder.add_ns(len(dataslot)) # 添加主机
        # 添加交换机，及和主机的连接
        for i in range(len(dataslot)):
            topobulider.add_ovs_switch(i)
            p1 = "s{}-h{}".format(i, i)
            p2 = "h{}-s{}".format(i, i)
            topobulider.add_veth(p1, p2, 1)
            os.system("sudo ovs-vsctl add-port s{} {}".format(i, p1))
            os.system("sudo ip link set {} netns h{}".format(p2, i))
            # 设置主机ip
            os.system("sudo ip netns exec h{} addr add 192.168.66.{}/24 dev {}".format(i, i+1, p2))
            # os.system("ip -n h{} link set {} up".format(i, p2))

        for key in dataslot:
            for i in range(len(dataslot[key])):
                p1 = "s{}-s{}".format(key, dataslot[key][i][0])
                p2 = "s{}-s{}".format(dataslot[key][i][0], key)
                if(((p1, p2) in topobulider.veth_set) or ((p2, p1) in topobulider.veth_set)):
                    continue
                topobulider.add_veth(p1, p2, float(dataslot[key][i][2])*1000)
                os.system("sudo ovs-vsctl add-port s{} {}".format(key, p1))
                os.system("sudo ovs-vsctl add-port s{} {}".format(dataslot[key][i][0], p2))

    @staticmethod
    def del_slot() -> None:
        # 删除一个时间片拓扑，清空
        for p in topobulider.veth_set:
            topobulider.del_veth(p[0], p[1])
        for s in topobulider.sw_set:
            topobulider.del_ovs_switch(s)
        nsbuilder.clear()
        topobulider.sw_set.clear()
        topobulider.veth_set.clear()
    
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
        topobulider.veth_set.add((p1, p2))
        topobulider.add_tc(p1, delay, 10)
        topobulider.add_tc(p2, delay, 10)
        os.system("echo \"add a links between {} done\"".format(p1))

    @staticmethod
    def del_veth(p1, p2):
        # delete a pair of veth(only need to delete one, another one will auto delete)删除一个veth对
        topobulider.del_tc(p1)
        topobulider.del_tc(p2)
        os.system("sudo ip link delete {}".format(p1))
        os.system("echo \"delete a links between {} done\"".format(p1))

    @staticmethod
    def add_ovs_switch(switch_id):
        # add a switch into net 添加一个ovs交换机
        ovs_name = "s{}".format(switch_id)
        os.system(
            "sudo ovs-vsctl add-br {} -- set bridge {} protocols=OpenFlow10,OpenFlow11,OpenFlow12,OpenFlow13 other-config:datapath-id={}".format(
                ovs_name, ovs_name, switch_id))
        topobulider.sw_set.add(switch_id)
        os.system("echo \"add a switch s{} done\"".format(switch_id))

    @staticmethod
    def del_ovs_switch(switch_id):
        # delete a switch from net 删除一个ovs交换机
        ovs_name = "s{}".format(switch_id)
        os.system("sudo ovs-vsctl del-br {} ".format(ovs_name))
        os.system("echo \"delete a switch s{} done\"".format(switch_id))