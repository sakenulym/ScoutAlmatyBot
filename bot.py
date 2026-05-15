import oracledb
from config import ORA_USER, ORA_PASS, ORA_DSN, ORA_WALLET

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        kwargs = dict(user=ORA_USER, password=ORA_PASS, dsn=ORA_DSN, min=1, max=5, increment=1)
        if ORA_WALLET:
            kwargs["wallet_location"] = ORA_WALLET
            kwargs["wallet_password"] = ORA_PASS
        _pool = oracledb.create_pool(**kwargs)
    return _pool


def get_conn():
    return get_pool().acquire()
