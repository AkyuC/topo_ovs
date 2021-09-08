import os
from topo.ctrlslot import ctrlslot

if __name__ == '__main__' :
    #获取当前文件路径，读取配置文件需要
    filePath = os.path.dirname(__file__)

    sw_num = 0
    with open(file=filePath + "/config/timeslot/test_0") as file:
        line = file.readline().strip("\n")
        sw_num = int(line) # 获取卫星交换机的数量
    
    for index in range(sw_num):
        # docker import --change 'CMD ["/usr/bin/supervisord"]' ovs.tar ovs
        os.system("sudo docker create -it --name=s{} --net=none --privileged -v /etc/localtime:/etc/localtime:ro ovs /bin/bash".format(index))
        # os.system("sudo docker create -it --name=s{} --net=host -v /etc/localtime:/etc/localtime:ro ovs /bin/bash".format(index))
        # os.system("sudo docker start s{} > /dev/null; sudo docker stop s{} > /dev/null".format(index,index))

    cslot = ctrlslot(filePath + "/config")
    ctrl_set = list()
    for slot_no in cslot.ctrl_slot:
        for ctrl in cslot.ctrl_slot[slot_no]:
            if ctrl not in ctrl_set:
                ctrl_set.append(ctrl)
                # print(ctrl)
    ctrl_set.sort()
    for ctrl in ctrl_set:
        # docker import --change 'CMD ["/usr/bin/supervisord"]' openmul.tar openmul
        os.system("sudo docker create -it --name=c{} --net=none --privileged -v /etc/localtime:/etc/localtime:ro openmul /bin/bash".format(ctrl))
        # os.system("sudo docker start c{} > /dev/null; sudo docker stop c{} > /dev/null".format(ctrl,ctrl))

    with open(file=filePath + "/config/rt_ctrl2db/db_deploy") as file:
        # docker import --change 'CMD ["/usr/bin/supervisord"]' database.tar database
        lines = file.read().splitlines()
        db_num = int((lines[0].split(' '))[0]) # 获取分布式数据库的数量
        db_data = lines[1].strip(' ').split(' ')   # 获取分布式数据库的位置
        db_data = list(map(int, db_data))
        for db in db_data:
            os.system("sudo docker create -it --name=db{} --net=none --privileged -v /etc/localtime:/etc/localtime:ro database /bin/bash".format(db))
            # os.system("sudo docker start db{} > /dev/null; sudo docker stop db{} > /dev/null".format(db,db))