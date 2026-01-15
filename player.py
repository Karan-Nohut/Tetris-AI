from board import Direction, Rotation, Action
from random import Random

class Player:
    def choose_action(self, board):
        raise NotImplementedError

class MyPlayer(Player):
    def __init__(self, seed=None):
        self.random = Random(seed)
        self.planned_actions = []  # queue of actions

    def calc_heights(self,board):
        heights = [0] * board.width
        for x in range(board.width):
            h = 0
            for y in range(board.height):
                if (x, y) in board.cells:
                    h = board.height - y
                    break
            heights[x] = h

        return heights

    def calculate_move_score(self, board, old_cells):
        score = 0
        line_clear_scores = [500, -500, -100, 2000, 10**12, -10**12]
        
        max_height_weight = 120
        roughness_weight = 35          
        hole_amount_weight = 700
        hole_depth_weight = 10
        adj_tiles_weight = 60
        adj_walls_weight = 50
        cliff_weight = 250
        shadow_weight = 30
        bubble_weight = 10

        lines_cleared = 0
        expected_cells = len(old_cells) + 4
        actual_cells = len(board.cells)
        missing = expected_cells - actual_cells
        if missing > 0:
            lines_cleared = missing // board.width
        lines_cleared = max(0, min(lines_cleared, 5))
        score += line_clear_scores[lines_cleared]

        heights = self.calc_heights(board)
        max_height = max(heights)
        score -= max_height * max_height_weight

        roughness = sum(abs(heights[x] - heights[x+1]) for x in range(board.width-1))
        score -= roughness * roughness_weight

        holes = 0
        hole_depth = 0
        for x in range(board.width):
            block_found = False
            col_height = heights[x]
            for y in range(board.height):
                if (x, y) in board.cells:
                    block_found = True
                elif block_found:
                    holes += 1
                    hole_depth += (board.height - y) - col_height
        score -= holes * hole_amount_weight
        score -= hole_depth * hole_depth_weight

        adj_tiles = 0
        if getattr(board.falling, 'cells', None):
            for (x, y) in board.falling.cells:
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    if (x+dx, y+dy) in board.cells:
                        adj_tiles += 1
        score += adj_tiles * adj_tiles_weight

        adj_walls = 0
        if getattr(board.falling, 'cells', None):
            for (x, y) in board.falling.cells:
                if x == 0 or x == board.width-1 or y == 0 or y == board.height-1:
                    adj_walls += 1
        score += adj_walls * adj_walls_weight

        cliff_left = cliff_right = 0
        for x in range(board.width):
            if x > 0:
                cliff_left = max(heights[x] - heights[x-1] - 1, -1)
            if x < board.width-1:
                cliff_right = max(heights[x] - heights[x+1] - 1, -1)
        score -= cliff_left * cliff_weight
        score -= cliff_right * cliff_weight

        shadows = 0
        bubbles = 0
        if getattr(board.falling, 'cells', None):
            falling_cells = board.falling.cells
            left = min(x for x, _ in falling_cells)
            right = max(x for x, _ in falling_cells)
            top = min(y for _, y in falling_cells)
            bottom = max(y for _, y in falling_cells)
            for x in range(left, right + 1):
                for y in range(top, bottom + 1):
                    if (x, y) not in falling_cells:
                        continue
                    solid_below = False
                    for s in range(y + 1, board.height):
                        if (x, s) in falling_cells:
                            break
                        if (x, s) in board.cells:
                            solid_below = True
                        else:
                            if not solid_below:
                                shadows += 1
                            else:
                                bubbles += 1
        score -= shadows * shadow_weight
        score -= bubbles * bubble_weight

        return score

    def return_best_moves(self, board):
        best_score = -10**15
        best_rot = 0
        best_shift = 0
                        
        for rot in range(4):
            for target_x in range(board.width):

                test = board.clone()

                # --- ROTATE CURRENT BLOCK ---
                for _ in range(rot):
                    if test.falling is None:
                        break
                    try:
                        test.rotate(Rotation.Clockwise)
                    except:
                        test.falling = None
                        break

                if test.falling is None:
                    continue

                cx = int(test.falling.center[0])
                shift = target_x - cx

                # --- MOVE CURRENT BLOCK ---
                if shift < 0:
                    for _ in range(-shift):
                        if test.falling is None:
                            break
                        try:
                            test.move(Direction.Left)
                        except:
                            test.falling = None
                            break

                elif shift > 0:
                    for _ in range(shift):
                        if test.falling is None:
                            break
                        try:
                            test.move(Direction.Right)
                        except:
                            test.falling = None
                            break

                if test.falling is None:
                    continue

                # --- DROP CURRENT BLOCK ---
                try:
                    test.move(Direction.Drop)
                except:
                    test.falling = None

                old_cells = set(test.cells)
                if test.falling is not None: 
                    for next_rot in range(4):
                        for next_target_x in range(test.width):

                            test2 = test.clone()

                            # --- ROTATE NEXT BLOCK ---
                            for _ in range(next_rot):
                                if test2.falling is None:
                                    break
                                try:
                                    test2.rotate(Rotation.Clockwise)
                                except:
                                    test2.falling = None
                                    break

                            if test2.falling is None:
                                continue

                            nx = int(test2.falling.center[0])
                            next_shift = next_target_x - nx

                            # --- MOVE NEXT BLOCK ---
                            if next_shift < 0:
                                for _ in range(-next_shift):
                                    if test2.falling is None:
                                        break
                                    try:
                                        test2.move(Direction.Left)
                                    except:
                                        test2.falling = None
                                        break

                            elif next_shift > 0:
                                for _ in range(next_shift):
                                    if test2.falling is None:
                                        break
                                    try:
                                        test2.move(Direction.Right)
                                    except:
                                        test2.falling = None
                                        break

                            if test2.falling is None:
                                continue

                            # --- DROP NEXT BLOCK ---
                            try:
                                test2.move(Direction.Drop)
                            except:
                                test2.falling = None
                                continue

                            # Score next placement
                            s = self.calculate_move_score(test2, old_cells)
                            if s > best_score:
                                best_score = s
                                best_rot = rot
                                best_shift = shift

        return best_rot, best_shift

    def build_action_plan(self, rot, shift):
        plan = []

        for _ in range(rot):
            plan.append(Rotation.Clockwise)

        if shift < 0:
            for _ in range(-shift):
                plan.append(Direction.Left)
        elif shift > 0:
            for _ in range(shift):
                plan.append(Direction.Right)

        plan.append(Direction.Drop)

        return plan

    def choose_action(self, board):

        if max(self.calc_heights(board)) > 16:

            heights = self.calc_heights(board)

            highest_height = max(heights)
            target_x = heights.index(highest_height)

            bomb_x = int(board.falling.center[0])

            if bomb_x < target_x:
                return Direction.Right
            elif bomb_x > target_x:
                return Direction.Left
            else:
                return Action.Bomb

        if self.planned_actions:
            test = board.clone()
            action = self.planned_actions[0]
            try:
                if isinstance(action, Direction):
                    test.move(action)
                elif isinstance(action, Rotation):
                    test.rotate(action)
            except:
                self.planned_actions = []
            else:
                return self.planned_actions.pop(0)

        rot, shift = self.return_best_moves(board)
        self.planned_actions = self.build_action_plan(rot, shift)
        return self.planned_actions.pop(0)

SelectedPlayer = MyPlayer