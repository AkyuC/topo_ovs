from multiprocessing import Queue


# 用于传向控制命令的队列
class command_queue:
    cq = Queue(1000) # 控制器消息队列

    @staticmethod
    def empty():
        #判断是否为空
        return command_queue.cq.empty()

    @staticmethod
    def write_queue(command):
        # 将指令放入队列
        if command_queue.cq.full():
            return False
        command_queue.cq.put(command)
        return True
    
    @staticmethod
    def read_queue():
        # 取出指令
        if command_queue.cq.empty():
            return False
        return command_queue.cq.get()

    @staticmethod
    def read_queue_wait():
        # 阻塞等待，取出指令
        return command_queue.cq.get()