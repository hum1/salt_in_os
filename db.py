import MySQLdb
import sys
from conf import DATABASES

def conn(DB="default"):
    database=DATABASES[DB]
    print database
    conn=MySQLdb.connect(user=database["USER"],passwd=database["PASSWORD"],host=database["HOST"],db=database["NAME"])
    return conn
