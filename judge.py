import json
from asyncio import sleep
import aiohttp
from gomoku.gomoku_referee import GomokuReferee
from gomoku.tic_tac_toe_referee import ticTacToeReferee
from gomoku.referee import Referee, Player
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
import requests
import asyncio
import logging
import time
import sys

judge_count = 0


async def judge():
    global judge_count
    api = sys.argv[1]
    while api[-1] == "/":
        api = api[:-1]
    access_token = sys.argv[2]
    while True:
        try:
            r = None
            async with aiohttp.ClientSession() as session:
                r = await session.get(api+"/api/judge?access_token={}".format(access_token))
                response = await r.text(encoding="utf-8")
            if response.strip() == "null":
                await sleep(1)
                continue
            judgeData = json.loads(response)
            match_id = judgeData["ID"]
            gameID = judgeData["GameID"]
            players = judgeData["Players"]
            time_limit_ns = judgeData["TimeLimitNs"]
            memory_limit_bytes = judgeData["MemoryLimitBytes"]
            if gameID == 1:
                r = GomokuReferee(
                    [Player(0, player["CodeContent"]["Language"],
                            player["CodeContent"]["Content"]) for player in players],
                    time_limit_ns,
                    memory_limit_bytes)

            elif gameID == 2:
                r = ticTacToeReferee(
                    [Player(0, player["CodeContent"]["Language"],
                            player["CodeContent"]["Content"]) for player in players],
                    time_limit_ns,
                    memory_limit_bytes)
            time1 = time.time()
            await r.run()
            time2 = time.time()
            postData = {
                "ID": match_id,
                "Token": judgeData["JudgeToken"],
                "MatchStates": [
                    {
                        "PlayersScore": json.dumps(state.players_score),
                        "Index": state.index,
                        "Detail": state.detail,
                        "Status": state.status,
                        "InputData": state.input_data,
                        "OutputData": state.output_data,
                        "TimeUsageNs": state.time_usage_ns,
                        "MemoryUsageBytes": state.memory_usage_bytes,
                    }
                    for state in r.states
                ]
            }
            judge_count = judge_count+1
            async with aiohttp.ClientSession() as session:
                r = await session.post(api+"/api/judge?access_token={}".format(access_token), json=postData)
                response = await r.text(encoding="utf-8")
            time3 = time.time()
            print(time2-time1, time3-time2, time1,
                  time2, judge_count, flush=True)
        except Exception as e:
            print("Exception : ", e, flush=True)
            await sleep(3)


if __name__ == '__main__':
    logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)
    get_event_loop().run_until_complete(judge())
