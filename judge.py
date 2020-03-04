import json
from asyncio import sleep
import aiohttp
from gomoku.gomoku_referee import GomokuReferee
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

api = "http://192.168.3.13:49900"


async def judge():
    event_loop = get_event_loop()
    while True:
        try:
            r = None
            async with aiohttp.ClientSession().get(api+"/judge") as r:
                response = await r.text(encoding="utf-8")
            if response.strip() == "null":
                await sleep(1)
                continue
            judgeData = json.loads(response)
            match_id = judgeData["ID"]
            gameID = judgeData["GameID"]
            players = judgeData["Players"]
            if gameID == 1:
                r = GomokuReferee(
                    [Player(0, player["CodeContent"]["Language"], player["CodeContent"]["Content"]) for player in players])
                await r.run()
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
                            "OutputData": state.output_data
                        }
                        for state in r.states
                    ]
                }
                async with aiohttp.ClientSession().post(api+"/judge", json=postData) as r:
                    response = await r.text(encoding="utf-8")
                print(response)
        except Exception as e:
            print("Exception : ", e)
            await sleep(1)


async def start_judge():
    try_init_cgroup()
    event_loop = get_event_loop()
    threadNum = 1
    for i in range(0, threadNum):
        event_loop.create_task(judge())


if __name__ == '__main__':
    logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)
    get_event_loop().run_until_complete(start_judge())
    pending = asyncio.Task.all_tasks()
    get_event_loop().run_until_complete(asyncio.gather(*pending))
