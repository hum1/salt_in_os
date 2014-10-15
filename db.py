import MySQLdb
import sys
from conf import DATABASES

def connection(DB="default"):
    database=DATABASES[DB]
    conn=MySQLdb.connect(user=database["USER"],passwd=database["PASSWORD"],host=database["HOST"],db=database["NAME"])
    return conn
