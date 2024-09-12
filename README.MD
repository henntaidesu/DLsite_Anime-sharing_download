##  本程序可用于在Anime-sharing中检索查找DLsite作品 

数据库采用mysql数据库，用于方便管理已下载作品。也有非数据库模式。

``` ini
[database]
host = host
port = port
user = user
password = password
database = database
open_db = False

[start_type]
type = GUI

[processes]
processes = 5

[DownPath]
downpath = O:\Test

[katfile]
ifkatfiledown = True
user = 
passwd = 
xfss = 

[Proxy]
openproxy = True
host = 127.0.0.1
port = 10809
type = http

[LogLevel]
level = error

[encoding]
encoding = cp437


```

