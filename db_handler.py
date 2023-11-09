import mysql.connector
from mysql.connector import pooling

dbconfig = {
        "host":'campaigntrailmojo.mysql.eu.pythonanywhere-services.com',
        "user":'campaigntrailmoj',
        "password":'PWD4MYSQL!',
        "database":'campaigntrailmoj$default'
    }

conn_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",
                                                        pool_size=5,
                                                        **dbconfig)

def get_connection():
    return conn_pool.get_connection()