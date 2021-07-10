# /usr/sbin/dynomite
# /usr/bin/redis-cli    /usr/bin/redis-server
class dbload:
    def __init__(self, filename:str) -> None:
        with open(file=filename) as file:
            lines = file.read().splitlines()
            self.db_num = int((lines[0].strip(' ').split(' '))[0]) # 获取分布式数据库的数量
            self.db_data = list(map(int, lines[1].strip(' ').split(' ')))    # 获取分布式数据库的位置

    # def load_db(self):