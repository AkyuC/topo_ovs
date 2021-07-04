import os, sys


if __name__ == '__main' :
    #获取当前文件路径，读取配置文件需要
    filePath = sys.argv[0]

    sw_num = 0
    with open(file=filePath + "\config\timeslot\test_0") as file:
        line = file.readline().strip(" ")
        sw_num = int(line) # 获取卫星交换机的数量
    
    for index in range(sw_num):
        os.system("sudo docker run -it --name=s{} --privileged ovs".format(index))
        os.system("sudo docker run -it --name=c{} --privileged openmul".format(index))