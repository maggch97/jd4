import sys
import traceback
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

# TODO judge能够返回的状态只有4种
# MATCH_STATE_END
# MATCH_STATE_CONTINUE
# MATCH_STATE_STATUS_OUTPUT_INVALID
# MATCH_STATE_PLAYER_OPERATION_INVALID

# 本轮结束后对局结束
MATCH_STATE_END = 0
# 本轮结束后对局仍继续
MATCH_STATE_CONTINUE = 1
# 玩家操作犯规
MATCH_STATE_PLAYER_OPERATION_INVALID = 2
# 本轮玩家代码输出格式错误
MATCH_STATE_OUTPUT_INVALID = 3

# 本轮玩家代码编译错误
MATCH_STATE_COMPILE_ERROR = 4
# 本轮玩家代码运行错误
MATCH_STATE_RUNTIME_ERROR = 5
# 对局轮次超过上限
MATCH_STATE_NUMBER_EXCEED_LIMIT = 6
# 输出超过上限
MATCH_STATE_OUTPUT_LIMIT_EXCEEDED = 7
# 运行时间超过上限
MATCH_STATE_TIME_LIMIT_EXCEEDED = 8
# 运行内存超过上限
MATCH_STATE_MEMORY_LIMIT_EXCEEDED = 9


class Output:
    def __init__(self, output_str: str):
        self.data = output_str.split(" ")
        self.index = 0

    def read_int(self) -> int:
        if len(self.data) <= self.index:
            raise Exception("len(self.data) <= self.index")
        self.index += 1
        # print("self.index ", self.index)
        # print(self.data)
        return int(self.data[self.index - 1])


CODE_LANGUAGE_C = 1
CODE_LANGUAGE_CPP = 2
CODE_LANGUAGE_PYTHON3 = 3


class Player:
    def __init__(self, player_type: int, language: int, code: str):
        self.type = player_type
        if language == CODE_LANGUAGE_CPP:
            self.lang = "cc"
        elif language == CODE_LANGUAGE_C:
            self.lang = "c"
        elif language == CODE_LANGUAGE_PYTHON3:
            self.lang = "py3"
        else:
            # TODO 测试暂时先全都定位c++
            self.lang = "cc"
            # raise Exception("unsupported language")
        self.code = code
        self.build = None


class MatchState:
    def __init__(self, index: int, status: int, detail: str, players_score: list, input: str, output: str):
        self.index = index
        self.status = status
        self.detail = detail
        self.players_score = players_score.copy()
        self.input_data = input
        self.output_data = output


class Referee:

    def __init__(self, players: List[Player]):
        self.time_limit_ns = 1 * 1000 * 1000 * 1000
        self.memory_limit_bytes = 256 * 1024 * 1024
        self.process_limit = 64
        self.output_limit_bytes = 1024
        self.states = []
        self.players = players
        self.current_input = None
        self.current_output = None

    # TODO 下面四个方法都应该是纯虚函数，python不知道怎么写暂时就这么苟着了
    def get_first_player(self) -> int:
        raise Exception("unimplemented")

    def get_input(self) -> str:
        raise Exception("unimplemented")

    def judge(self, output: Output) -> Tuple[str, int, list, int]:
        raise Exception("unimplemented")

    def judge_error(self) -> Tuple[str, list]:
        raise Exception("unimplemented")

    def do_input(self, input_file):
        try:
            with open(input_file, 'w') as inputIO:
                input_str = self.get_input()
                self.current_input = input_str
                inputIO.write(input_str)
        except Exception as e:
            print(e)
            raise e

    def get_output(self, output_file) -> (str, bool):
        try:
            with open(output_file, "r") as outputIO:
                output = outputIO.read(self.output_limit_bytes)
                self.current_output = output
                end = outputIO.read(1)
                output_limit_exceeded = (end != "")
                return output, output_limit_exceeded
        except Exception as e:
            print(e)
            raise e

    async def run(self):
        loop = get_event_loop()
        for player in self.players:
            if player.build is None:
                player.build = await build(player.lang, player.code.encode("UTF-8"))

        next_player = self.get_first_player()
        # TODO 目前评测端只支持完整评测整个对局
        # 服务端有一个MatchIndex为1的起始状态
        # 所以MatchIndex每次从2开始
        MatchIndex = 1
        try:
            while True:
                MatchIndex += 1
                sandbox, = await get_sandbox(1)
                try:
                    if self.players[next_player].build[0] is not None:
                        executable = await self.players[next_player].build[0].install(sandbox)
                        stdin_file = path.join(sandbox.in_dir, 'stdin')
                        mkfifo(stdin_file)
                        stdout_file = path.join(sandbox.in_dir, 'stdout')
                        mkfifo(stdout_file)
                        stderr_file = path.join(sandbox.in_dir, 'stderr')
                        mkfifo(stderr_file)
                        with socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as cgroup_sock:
                            cgroup_sock.bind(
                                path.join(sandbox.in_dir, 'cgroup'))
                            cgroup_sock.listen()
                            execute_task = loop.create_task(executable.execute(
                                sandbox,
                                stdin_file='/in/stdin',
                                stdout_file='/in/stdout',
                                stderr_file='/in/stderr',
                                cgroup_file='/in/cgroup'))
                            others_task = gather(
                                loop.run_in_executor(
                                    None, self.do_input, stdin_file),
                                loop.run_in_executor(
                                    None, self.get_output, stdout_file),
                                read_pipe(stderr_file, MAX_STDERR_SIZE),
                                wait_cgroup(cgroup_sock,
                                            execute_task,
                                            self.time_limit_ns,
                                            self.time_limit_ns,
                                            self.memory_limit_bytes,
                                            self.process_limit))
                            execute_status = await execute_task
                            # print("execute_status", execute_status)
                            _, (output_str, output_limit_exceeded), stderr, (time_usage_ns, memory_usage_bytes) = \
                                await others_task
                            if output_limit_exceeded:
                                detail, score = self.judge_error()
                                self.states.append(
                                    MatchState(MatchIndex, MATCH_STATE_OUTPUT_INVALID, detail, score, self.current_input, self.current_output))
                                break
                            elif time_usage_ns > self.time_limit_ns:
                                detail, score = self.judge_error()
                                self.states.append(
                                    MatchState(MatchIndex, MATCH_STATE_TIME_LIMIT_EXCEEDED, detail, score, self.current_input, self.current_output))
                                break
                            elif memory_usage_bytes > self.memory_limit_bytes:
                                detail, score = self.judge_error()
                                self.states.append(
                                    MatchState(MatchIndex, MATCH_STATE_MEMORY_LIMIT_EXCEEDED, detail, score, self.current_input, self.current_output))
                                break
                            elif execute_status != 0:
                                detail, score = self.judge_error()
                                self.states.append(
                                    MatchState(MatchIndex, MATCH_STATE_RUNTIME_ERROR, detail, score, self.current_input, self.current_output))
                                break
                            else:
                                detail, status, score, next_player = (
                                    self.judge(Output(output_str)))
                                self.states.append(MatchState(
                                    MatchIndex, status, detail, score, self.current_input, self.current_output))
                                # print(detail, status, score, next_player)
                                # print(output_str)
                                if status == MATCH_STATE_END:
                                    break
                                elif status == MATCH_STATE_PLAYER_OPERATION_INVALID or status == MATCH_STATE_OUTPUT_INVALID:
                                    break
                                elif status == MATCH_STATE_CONTINUE:
                                    pass
                                else:
                                    raise Exception(
                                        "status = {}".format(status))
                    else:
                        print(self.players[next_player].build)
                        detail, score = self.judge_error()
                        # print(self.players[next_player].build[1])
                        self.states.append(
                            MatchState(MatchIndex, MATCH_STATE_COMPILE_ERROR, detail, score, "", ""))
                        break
                finally:
                    put_sandbox(sandbox)
        except Exception as e:
            print(e)
            traceback.print_exc(file=sys.stdout)
            pass
