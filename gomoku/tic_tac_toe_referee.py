
from gomoku.referee import Output
from gomoku import referee
from typing import Tuple, List
import json


class ticTacToeReferee(referee.Referee):
    def __init__(self, players: List[referee.Player], time_limit_ns: int, memory_limit_bytes: int):
        self.player_count = 2
        if len(players) != self.player_count:
            raise Exception(
                "length of players:{} is not equal to player_count:{}".format(len(players), self.player_count))
        super().__init__(players, time_limit_ns, memory_limit_bytes)
        self.chessboard = [[0 for i in range(3)] for j in range(3)]
        # 两名玩家得分
        self.score = [0, 0]
        # 记录当前运行的玩家
        self.player_index = 0

    def get_first_player(self) -> int:
        # 对局最开始会调用这个方法获得第一个操作的玩家
        # 返回的是players的下标，从0开始
        return 0

    def get_winner(self):
        for i in range(3):
            if self.chessboard[i][0] != 0:
                if self.chessboard[i][0] == self.chessboard[i][1] and self.chessboard[i][1] == self.chessboard[i][2]:
                    return self.chessboard[i][0]
            if self.chessboard[0][i] != 0:
                if self.chessboard[0][i] == self.chessboard[1][i] and self.chessboard[1][i] == self.chessboard[2][i]:
                    return self.chessboard[0][i]
        if self.chessboard[0][0] != 0:
            if self.chessboard[0][0] == self.chessboard[1][1] and self.chessboard[1][1] == self.chessboard[2][2]:
                return self.chessboard[0][0]
        if self.chessboard[0][2] != 0:
            if self.chessboard[0][2] == self.chessboard[1][1] and self.chessboard[1][1] == self.chessboard[2][0]:
                return self.chessboard[0][2]
        for i in range(3):
            for j in range(3):
                if self.chessboard[i][j] == 0:
                    return 0
        # 平局
        return -1

    def judge(self, output: Output) -> Tuple[str, int, list, int]:
        # 每次玩家运行输出后会调用judge方法
        # 返回值分别是 序列化后的棋局状态文本，本轮状态，分数列表，下一个操作的玩家下标
        r = int
        c = int
        try:
            r = output.read_int()
            c = output.read_int()
        except Exception as e:
            # 输出格式错误
            self.score[(self.player_index + 1) % self.player_count] = 2
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_OUTPUT_INVALID, self.score, 0
        if r < 0 or r >= 3 or c < 0 or c >= 3:
            # 落子超过范围，犯规
            self.score[(self.player_index + 1) % self.player_count] = 2
            return json.dumps({"chessboard": self.chessboard}), referee.MATCH_STATE_PLAYER_OPERATION_INVALID, self.score, 0
        if self.chessboard[r][c] != 0:
            # 落子位置非空，犯规
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
        # 玩家由于运行超时，内存超限等原因导致无法judge时，会调用judge_error
        # 返回值分别是 序列化后的棋局状态文本，分数列表，
        self.score[(self.player_index + 1) % self.player_count] = 2
        return json.dumps({"chessboard": self.chessboard}), self.score

    def get_input(self) -> str:
        # 每次玩家运行前会调用这个函数获得玩家的输入
        input_str = str(self.player_index + 1) + "\n"
        for i in range(3):
            for j in range(3):
                input_str += str(self.chessboard[i][j]) + " "
            input_str += "\n"
        return input_str
