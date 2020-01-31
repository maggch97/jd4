from typing import Tuple

from gomoku import referee
from io import TextIOWrapper

from gomoku.referee import Output


class GomokuReferee(referee.Referee):
    def __init__(self):
        super().__init__()
        self.chessboard = [[0 for i in range(15)] for j in range(15)]
        self.score = [0, 0]
        self.player_index = 0
        self.player_count = 2
        self.judge_count = 0

        self.judge_count_limit = 100

    def judge(self, output: Output) -> Tuple[str, int, list, int]:
        r = int
        c = int
        try:
            r = output.read_int()
            c = output.read_int()
        except Exception as e:
            self.score[(self.player_index + 1) % self.player_count] = 1
            return "{}", referee.MATCH_STATE_STATUS_OUTPUT_INVALID, self.score, 0

        if r < 0 or r > 15 or c < 0 or c > 15:
            self.score[(self.player_index + 1) % self.player_count] = 1
            return "{}", referee.MATCH_STATE_PLAYER_OPERATION_INVALID, self.score, 0
        if self.chessboard[r][c] != 0:
            self.score[(self.player_index + 1) % self.player_count] = 1
            return "{}", referee.MATCH_STATE_PLAYER_OPERATION_INVALID, self.score, 0
        self.chessboard[r][c] = self.player_index + 1
        # TODO 写check

        self.player_index = (self.player_index + 1) % self.player_count
        return "", referee.MATCH_STATE_CONTINUE, self.score, self.player_index

    def get_input(self) -> str:
        input_str = str(self.player_index + 1) + "\n"
        for i in range(15):
            for j in range(15):
                input_str += str(self.chessboard[i][j]) + " "
            input_str += "\n"
        return input_str
