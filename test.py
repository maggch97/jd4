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

MAX_STDERR_SIZE = 8192


async def test():
    result = await build("c", "#include<stdio.h>\nint main(){}".encode("UTF-8"))
    package = result[0]
    print(package)
    cases = read_cases("/home/maggch/PycharmProjects/jd4/jd4/testdata/aplusb-legacy.zip")
    print(cases)
    for case in cases:
        result = await case.judge(package)
        print(result)


class Referee:
    def __init__(self):
        self.time_limit_ns = 1 * 1000 * 1000 * 1000
        self.memory_limit_bytes = 1 * 1024 * 1024
        self.process_limit = 64
        self.state = ""

    def do_input(self, input_file):
        try:
            with open(input_file, 'wb') as dst:
                dst.write(self.state.encode("UTF-8"))
        except BrokenPipeError:
            pass

    def do_output(self, output_file):
        try:
            with open(output_file, "rb") as dst:
                print(dst.readlines())
                return False
        except BrokenPipeError:
            pass

    async def run(self, state: str, lang: str, code: str):
        self.state = state
        loop = get_event_loop()
        result = await build(lang, code.encode("UTF-8"))
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
                _, correct, stderr, (time_usage_ns, memory_usage_bytes) = \
                    await others_task
                print(correct)
                print(time_usage_ns)
        finally:
            put_sandbox(sandbox)


try_init_cgroup()
event_loop = get_event_loop()
event_loop.run_until_complete(test())
r = Referee()
for i in range(0, 100):
    event_loop.run_until_complete(r.run("1 2", "c", "#include<stdio.h>\nint main(){printf(\"123132\");}"))
