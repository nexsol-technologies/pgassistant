import subprocess


def is_number(s):
    try:
        float(s) 
        return True
    except ValueError:
        return False


class pgTune:
    db_version="16"
    db_cpu=1
    db_memory="1GB"
    db_storage="ssd"
    db_type="web"
    db_maxconn=100
    db_tune={}

    def __init__(self, db_version, db_cpu, db_memory, db_storage, db_type, db_maxconn):
        self.db_version = db_version
        self.db_cpu = db_cpu
        self.db_memory = db_memory
        self.db_storage = db_storage
        self.db_type = db_type
        self.db_maxconn = db_maxconn

    def get_pg_tune(self):
        cmd = "pgtune.sh"
        self.db_tune={}
        result = subprocess.run(['bash', cmd , 
                                 '-u' , str(self.db_cpu),
                                '-m', self.db_memory,
                                '-v', self.db_version,
                                '-s', self.db_storage,
                                '-t', self.db_type,
                                '-c', str(self.db_maxconn)
                                ]
                                , stdout=subprocess.PIPE)
        lines = result.stdout.decode('utf-8').split("\n")
        for line in lines:
            if ("==" in line):
                values = line.split("==",1)
                parameter = values[0].strip()
                parameter_value = values[1].strip()
                self.db_tune[parameter]=parameter_value

        return self.db_tune

    def get_docker_cmd(self,db_config, db_version):
        docker_cmd = (
"services:\n"
f"  {db_config['db_name']}-db:\n"
"    restart: always\n"
f"    image: postgres:{db_version}-alpine\n"
"    ports: \n"
f"      - {db_config['db_port']}:5432\n"
"    deploy: \n"
"      resources: \n"
"         limits:\n"
f"          cpus: {self.db_cpu}.0\n"
f"          memory: {self.db_memory}\n"
"    environment:\n"
f"      - POSTGRES_USER={db_config['db_user']}\n"
"      - POSTGRES_PASSWORD=xxxxx\n"
f"      - POSTGRES_DB={db_config['db_user']}\n"            
        )
        docker_cmd=docker_cmd+"    command: >\n        postgres\n            -c shared_preload_libraries='pg_stat_statements'\n            -c autovacuum=on\n"
        for param in  self.db_tune:
            if is_number( self.db_tune[param]):
                docker_cmd = docker_cmd + f"            -c {param}={ self.db_tune[param]}\n"
            else: 
                docker_cmd = docker_cmd + f"            -c {param}='{ self.db_tune[param]}'\n"
        return docker_cmd
    

    def get_alter_system(self, running_values):
        sqlalter = ""
        for param in self.db_tune: 
            if param in running_values:  # Check if the key exists
                if self.db_tune[param] != running_values[param]:
                    if is_number(self.db_tune[param]):
                        sqlalter += f"ALTER SYSTEM SET {param}={self.db_tune[param]};\n"
                    else:
                        sqlalter += f"ALTER SYSTEM SET {param}='{self.db_tune[param]}';\n"
            else:
                print(f"Warning: Key '{param}' not found in running_values.")
        return sqlalter

