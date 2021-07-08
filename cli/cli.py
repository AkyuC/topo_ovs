import os
from threading import Thread
from ..controller import command_queue
from ..utils import const_command


class cli:
    def __init__(self) -> None:
        # 初始化
        self.status = False # 状态变量
        self.start()

    def __do_start(self):
        # cli界面线程
        while True:
            os.system("clear")
            try:
                print("> Available commands(number 0~8):\n"
                    "> 0.run topo\n"
                    "> 1.run service(iperf)\n"
                    "> 2.stop service(iperf)\n"
                    "> 3.switch shutdown test + switch number(0 ~ 66)\n"
                    "> 4.switch recover test + switch number(0 ~ 66)\n"
                    "> 5.controller shutdown test + controller number(0 ~ 15)\n"
                    "> 6.controller recover test + controller number(0 ~ 15)\n"
                    "> 7.database shutdown test + database number(0 ~ 3)\n"
                    "> 8.database recover test + database number(0 ~ 3)\n"
                    "> 9.stop all and exit\n"
                    )

                command = input(">Input commands:").split()
                if len(command) == 0:
                    os.system("clear")
                    continue
                # 写入消息队列中
                command_queue.write_queue(command)
                os.system("clear")
                if(command[0] == 8):
                    self.started = False
                    break
                
            except KeyboardInterrupt:
                # 键盘输入错误，关闭所有的设备，退出
                print("Error input! Exit！\n")
                # 通知其他线程关闭
                command_queue.write_queue(8)
                break
    
    def start(self):
        # 开启线程
        if self.status:
            return False
        else:
            Thread(target=self.__do_start).start()
            self.status = True
        return True

    def stop(self):
        # 关闭线程
        os.system(str(const_command.cli_stop_all))
        self.started = False
