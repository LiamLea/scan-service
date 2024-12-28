from scan_service.lib.vars import global_var
from sqlalchemy import create_engine,Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

if global_var.global_config.get("probe_service", 1):
    db_info = global_var.global_config["db_info"]

    Base = declarative_base()

    engine = create_engine(
        "mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8" %(db_info["user"], db_info["password"], db_info["host"], db_info["port"], db_info["db_name"]),
        max_overflow = 2,       #连接池满时，最多再创建多少个连接
        pool_size = 2,          #连接池大小
        pool_timeout = 30,      #等待获取连接池中连接的时长，如果超时，则报错
        pool_recycle = -1       #多久对连接池中的线程进行一次重置
    )

    Session = sessionmaker(bind = engine)

    class AtomSystem(Base):
        """
        cmdb_atomic_system
        存储的是原子系统的信息
        """
        __table__ = Table('cmdb_atomic_system', Base.metadata, autoload = True, autoload_with = engine)

    class AtomConfig(Base):
        __table__ = Table('cmdb_ci_instance_software_config', Base.metadata, autoload = True, autoload_with = engine)

    class ClusterInfo(Base):
        __table__ = Table('cmdb_software_cluster', Base.metadata, autoload = True, autoload_with = engine)

    class ClusterNode(Base):
        __table__ = Table('cmdb_software_cluster_node', Base.metadata, autoload = True, autoload_with = engine)

    class MonitorHost(Base):
        __table__ = Table('monitor_host', Base.metadata, autoload = True, autoload_with = engine)

    class HostConfig(Base):
        __table__ = Table('cmdb_ci_instance_host_config', Base.metadata, autoload = True, autoload_with = engine)

else:
    Session = AtomConfig = ClusterInfo = ClusterNode = MonitorHost = HostConfig = AtomSystem = ""

# session = Session()
# for obj in session.query(AtomSystem).all():
#     print(obj.ip)