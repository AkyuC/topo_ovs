import os
from threading import Thread
from controller.command_queue import command_queue
from utils.const_command import const_command


class cli:
    def __init__(self) -> None:
        # 初始化
        self.status = False # 状态变量

    def __do_start(self):
        # cli界面线程
        while True:
            os.system("clear")
            try:
                print("> Available commands(number 0~8):\n"
                    "> 0.run topo\n"
                    "> 1.run service(ping)\n"
                    "> 2.stop service(ping)\n"
                    "> 3.switch down and reload test + switch number(0 ~ 66)\n"
                    "> 4.controller down and reload test + controller number(0 ~ 15)\n"
                    "> 5.database down and reload test + database number(0 ~ 3)\n"
                    "> 6.stop all and exit\n"
                    )

                command = input(">Input commands:").strip()
                if len(command) == 0 or not float(command[0]):
                    os.system("clear")
                    continue
                # 写入消息队列中
                command_queue.write_queue(command)
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
