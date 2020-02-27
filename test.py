import json
from asyncio import sleep
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
code = '''
#include <random>
#include <iostream>

using namespace std;
int chessboard[15][15];

int main() {

    mt19937 mt(199793);
    int color;
    cin >> color;
    for (auto &i : chessboard) {
        for (int &j : i) {
            cin >> j;
        }
    }
    while (true) {
        int r = mt() % 15;
        int c = mt() % 15;
        if (chessboard[r][c] == 0) {
            cout << r << " " << c;
             cout << " \\n";
            for (auto &i : chessboard) {
                for (int &j : i) {
                    cout << j << " ";
                }
                cout << "\\n";
            }
            break;
        }
    }
    return 0;
}
'''


async def judge():
    event_loop = get_event_loop()
    while True:
        try:
            r = None
            response = requests.get(api+"/judge")
            judgeData = json.loads(response.text)
            match_id = judgeData["ID"]
            # print(judgeData)
            gameID = judgeData["GameID"]
            print(gameID)
            players = judgeData["Players"]
            # print(players)
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
                            "Status": state.status
                        }
                        for state in r.states
                    ]
                }
                response = requests.post(api+"/judge", json=postData)
                print("?????????????????????????")
                print(response.text)
        except Exception as e:
            print(e)
            await sleep(1)


async def start_judge():
    try_init_cgroup()
    event_loop = get_event_loop()
    threadNum = 5
    for i in range(0, threadNum):
        event_loop.create_task(judge())


if __name__ == '__main__':
    logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)
    get_event_loop().run_until_complete(start_judge())
    pending = asyncio.Task.all_tasks()
    get_event_loop().run_until_complete(asyncio.gather(*pending))
