class const_command(object):
    class const_commandError(TypeError):pass
 
    def __setattr__(self, name, value):
        if self.__dict__.has_key(name):
            raise self.const_commandError,"Can't rebind const_command(%s)" % name
        self.__dict__[name]=value
        
    def __delattr__(self, name):
        if name in self.__dict__:
            raise  self.const_commandError,"Can't unbind const_command(%s)" % name
        raise NameError,name

def const_command_load():
    # 命令常量定义
    # cli命令
    const_command.cli_run_topo = 0
    const_command.cli_run_ping = 1
    const_command.cli_stop_ping = 2
    const_command.cli_sw_reload = 3
    const_command.cli_ctrl_reload = 4
    const_command.cli_db_reload = 5
    const_command.cli_stop_all = 6
    # timer定时器切换命令
    const_command.timer_diff = 7