from gomoku.gomoku_referee import GomokuReferee
from gomoku.referee import Referee
from jd4.compile import build
from asyncio import get_event_loop, gather
from jd4.case import read_cases
from jd4.cgroup import try_init_cgroup
from jd4.pool import get_sandbox, put_sandbox
from os import link, mkfifo, path
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK
from jd4.util import read_pipe, parse_memory_bytes, parse_time_ns
from jd4.cgroup import wait_cgroup
from functools import partial



async def test():
    result = await build("c", "#include<stdio.h>\nint main(){}".encode("UTF-8"))
    package = result[0]
    print(package)
    cases = read_cases("/home/maggch/PycharmProjects/jd4/jd4/testdata/aplusb-legacy.zip")
    print(cases)
    for case in cases:
        result = await case.judge(package)
        print(result)





try_init_cgroup()
event_loop = get_event_loop()
event_loop.run_until_complete(test())
r = GomokuReferee()
for i in range(0, 1):
    event_loop.run_until_complete(r.run("1 2", "c", "#include<stdio.h>\nint main(){printf(\"-123132 123123123\");}"))
