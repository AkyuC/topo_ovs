import sys
from cli.cli import cli
from utils.const_command import const_command
from controller.controller import controller

if __name__ == '__main' :
    # 加载命令常量
    sys.modules[__name__] = const_command()

    #获取当前文件路径，读取配置文件需要
    filePath = sys.argv[0]

    # 控制调度器加载
    ctrl = controller(filePath)

    # cli加载
    user_cli = cli()