from typing import Tuple, List
import json
from gomoku import referee

from gomoku.referee import Output


class GomokuReferee(referee.Referee):
    def __init__(self, players: List[referee.Player], time_limit_ns: int, memory_limit_bytes: int):
        self.player_count = 2
        if len(players) != self.player_count:
            raise Exception(
                "length of players:{} is not equal to player_count:{}".format(len(players), self.player_count))
        super().__init__(players, time_limit_ns, memory_limit_bytes)
        self.chessboard = [[0 for i in range(15)] for j in range(15)]
        self.score = [0, 0]
        self.player_index = 0
        # TODO 下面两个参数暂时没用到
        self.judge_count = 0
        self.judge_count_limit = 100

    def get_first_player(self) -> int:
        return 0

    def is_five_chess_same(self, x, y, kx, ky) -> bool:
        chessboard = self.chessboard
        if self.chessboard[x][y] == 0:
            return False

        for i in range(1, 5):
            if (x + kx * i < 0) or (x + kx * i >= len(chessboard)) or (y + ky * i < 0) or (
                    y + ky * i >= len(chessboard[x + kx * i])):
                return False
            if chessboard[x + kx * i][y + ky * i] != chessboard[x][y]:
                return False
        return True

    def get_winner(self) -> int:
        chessboard = self.chessboard
        empty_count = 0
        for i in range(0, len(chessboard)):
            for j in range(0, len(chessboard[i])):
                empty_count = empty_count+1
                if chessboard[i][j] == 0:
                    continue
                if self.is_five_chess_same(i, j, 1, 0):
                    return chessboard[i][j]
                if self.is_five_chess_same(i, j, 1, 1):
                    return chessboard[i][j]
                if self.is_five_chess_same(i, j, 1, -1):
                    return chessboard[i][j]
                if self.is_five_chess_same(i, j, 0, 1):
                    return chessboard[i][j]
        if empty_count == 0:
            # 平局
            return -1
        return 0

    def judge(self, output: Output) -> Tuple[str, int, list, int]:
        r = int
        c = int
        try:
            r = output.read_int()
            c = output.read_int()
        except Exception as e:
            self.score[(self.player_index + 1) % self.player_count] = 2
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_OUTPUT_INVALID, self.score, 0

        if r < 0 or r > 15 or c < 0 or c > 15:
            self.score[(self.player_index + 1) % self.player_count] = 2
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_PLAYER_OPERATION_INVALID, self.score, 0
        if self.chessboard[r][c] != 0:
            self.score[(self.player_index + 1) % self.player_count] = 2
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_PLAYER_OPERATION_INVALID, self.score, 0
        self.chessboard[r][c] = self.player_index + 1
        winner = self.get_winner()

        if winner == 0:
            self.player_index = (self.player_index + 1) % self.player_count
            return json.dumps(
                {"chessboard": self.chessboard}), referee.MATCH_STATE_CONTINUE, self.score, self.player_index
        elif winner == -1:
            # 平局
            self.score[0] = 1
            self.score[1] = 1
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_END, self.score, 0
        else:
            self.score[winner - 1] = 2
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_END, self.score, 0

    def judge_error(self) -> Tuple[str, list]:
        self.score[(self.player_index + 1) % self.player_count] = 2
        return json.dumps({"chessboard": self.chessboard}), self.score

    def get_input(self) -> str:
        input_str = str(self.player_index + 1) + "\n"
        for i in range(15):
            for j in range(15):
                input_str += str(self.chessboard[i][j]) + " "
            input_str += "\n"
        return input_str
