from asyncio import get_event_loop, gather
from typing import Tuple, List, TextIO

from jd4.pool import get_sandbox, put_sandbox
from os import link, mkfifo, path
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK
from jd4.util import read_pipe, parse_memory_bytes, parse_time_ns
from jd4.cgroup import wait_cgroup
from functools import partial
from jd4.compile import build

MAX_STDERR_SIZE = 8192

# 本轮结束后对局结束
MATCH_STATE_END = 0
# 本轮结束后对局仍继续
MATCH_STATE_CONTINUE = 1
# 本轮玩家代码编译错误
MATCH_STATE_STATUS_COMPILE_ERROR = 2
# 本轮玩家代码运行错误
MATCH_STATE_STATUS_RUNTIME_ERROR = 3
# 本轮玩家代码输出格式错误
MATCH_STATE_STATUS_OUTPUT_INVALID = 4
# 对局轮次超过上限
MATCH_STATE_NUMBER_EXCEED_LIMIT = 5
# 玩家操作犯规
MATCH_STATE_PLAYER_OPERATION_INVALID = 6


class Output:
    def __init__(self, io: TextIO):
        self.io = io

    def read_int(self) -> int:
        length_limit = 10
        prev_str = ""
        not_start = True
        while True:
            chunk = self.io.read(1)
            if chunk:
                if chunk == " ":
                    print(not_start)
                    if not_start:
                        not_start = False
                    else:
                        break
                elif chunk in ['-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    not_start = False
                    prev_str += chunk
                    if len(prev_str) > length_limit:
                        raise Exception("length of prev_str exceeds limit")
                else:
                    raise Exception("{} is not valid value".format(chunk))
            else:
                break
        if len(prev_str) == 0:
            raise Exception("read_int failed")
        return int(prev_str)


class Player:
    def __init__(self, player_type: int, lang: str, code: str):
        self.type = player_type
        self.lang = lang
        self.code = code
        self.build = None


class MatchState:
    def __init__(self, index: int, status: int, detail: str, players_score: str):
        self.index = index
        self.status = status
        self.detail = detail
        self.players_score = players_score


class Referee:

    def __init__(self, players: List[Player]):
        self.time_limit_ns = 1 * 1000 * 1000 * 1000
        self.memory_limit_bytes = 1 * 1024 * 1024
        self.process_limit = 64
        self.state = ""
        self.players = players

    def get_first_player(self) -> int:
        raise Exception("unimplemented")

    def get_input(self) -> str:
        raise Exception("unimplemented")

    def judge(self, output: Output) -> Tuple[str, int, list, int]:
        raise Exception("unimplemented")

    def do_input(self, input_file):
        try:
            with open(input_file, 'w') as inputIO:
                inputIO.write(self.get_input())
        except Exception as e:
            print(e)
            raise e

    def do_output(self, output_file) -> Tuple[str, int, list, int]:
        try:
            with open(output_file, "r") as outputIO:
                return self.judge(Output(outputIO))
        except Exception as e:
            print(e)
            raise e

    async def run(self, state: str, lang: str, code: str):
        self.state = state
        loop = get_event_loop()
        for player in self.players:
            if player.build is not None:
                player.build = await build(player.lang, player.code.encode("UTF-8"))
        result = await build(lang, code.encode("UTF-8"))
        print(result)
        package = result[0]
        sandbox, = await get_sandbox(1)

        try:
            executable = await package.install(sandbox)
            stdin_file = path.join(sandbox.in_dir, 'stdin')
            mkfifo(stdin_file)
            stdout_file = path.join(sandbox.in_dir, 'stdout')
            mkfifo(stdout_file)
            stderr_file = path.join(sandbox.in_dir, 'stderr')
            mkfifo(stderr_file)
            with socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as cgroup_sock:
                cgroup_sock.bind(path.join(sandbox.in_dir, 'cgroup'))
                cgroup_sock.listen()
                execute_task = loop.create_task(executable.execute(
                    sandbox,
                    stdin_file='/in/stdin',
                    stdout_file='/in/stdout',
                    stderr_file='/in/stderr',
                    cgroup_file='/in/cgroup'))
                others_task = gather(
                    loop.run_in_executor(None, self.do_input, stdin_file),
                    loop.run_in_executor(None, self.do_output, stdout_file),
                    read_pipe(stderr_file, MAX_STDERR_SIZE),
                    wait_cgroup(cgroup_sock,
                                execute_task,
                                self.time_limit_ns,
                                self.time_limit_ns,
                                self.memory_limit_bytes,
                                self.process_limit))
                execute_status = await execute_task
                _, (detail, status, score, next_player), stderr, (time_usage_ns, memory_usage_bytes) = \
                    await others_task
                print(detail)
                print(time_usage_ns)

                next_player = self.get_first_player()
                while True:
                    if self.players[next_player].build[0] is None:
                        return Exce
        finally:
            put_sandbox(sandbox)
