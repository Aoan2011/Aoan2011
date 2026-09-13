import os
import re
import json
import sys
from datetime import datetime, timezone, timedelta

from github import Github

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_chart import generate_chart

BOARD_SIZE = 15
STATE_FILE = 'state.json'
STATS_FILE = 'stats.json'
README_FILE = 'README.md'
CHART_FILE = 'assets/stats.png'

SYMBOL = {'B': '●', 'W': '○', '.': '·'}
NAME = {'B': '黑方 ⚫', 'W': '白方 ⚪'}


# ---------- 工具函数 ----------

def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fresh_state(game_id=1):
    return {
        'board': ['.' * BOARD_SIZE for _ in range(BOARD_SIZE)],
        'turn': 'B',
        'winner': None,
        'last_move': None,
        'move_count': 0,
        'game_id': game_id,
        'recorded': False,
    }


def check_win(board, row, col, color):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == color:
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 5:
            return True
    return False


def scan_threats(board, color):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    open_three = 0
    open_four = 0

    def in_bounds(r, c):
        return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != color:
                continue
            for dr, dc in directions:
                pr, pc = r - dr, c - dc
                if in_bounds(pr, pc) and board[pr][pc] == color:
                    continue
                length = 0
                rr, cc = r, c
                while in_bounds(rr, cc) and board[rr][cc] == color:
                    length += 1
                    rr += dr
                    cc += dc
                before_open = in_bounds(pr, pc) and board[pr][pc] == '.'
                after_open = in_bounds(rr, cc) and board[rr][cc] == '.'
                if length == 4 and (before_open or after_open):
                    open_four += 1
                elif length == 3 and before_open and after_open:
                    open_three += 1
    return open_three, open_four


def predict_win_rate(board):
    b3, b4 = scan_threats(board, 'B')
    w3, w4 = scan_threats(board, 'W')
    b_score = b3 * 3 + b4 * 10 + 1
    w_score = w3 * 3 + w4 * 10 + 1
    total = b_score + w_score
    b_pct = round(b_score / total * 100)
    b_pct = max(5, min(95, b_pct))
    return b_pct, 100 - b_pct


def get_recent_games(stats, n=3):
    games = stats.get('games', [])
    return list(reversed(games[-n:]))


def get_active_players(stats, hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    counter = {}
    for m in stats.get('moves', []):
        ts = m.get('time')
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if t >= cutoff:
            user = m.get('user', 'unknown')
            counter[user] = counter.get(user, 0) + 1
    return sorted(counter.items(), key=lambda x: -x[1])[:5]


# ---------- ASCII 棋盘渲染（带高亮） ----------

def parse_coord(coord):
    if not coord or len(coord) < 2:
        return -1, -1
    try:
        col = ord(coord[0].upper()) - ord('A')
        row = int(coord[1:]) - 1
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return row, col
    except (ValueError, IndexError):
        pass
    return -1, -1


def render_board_ascii(board, last_move=None):
    lines = []
    lr, lc = parse_coord(last_move)

    header = '    ' + ' '.join(chr(ord('A') + i) for i in range(BOARD_SIZE))
    lines.append(header)

    for r in range(BOARD_SIZE):
        cells = []
        for c in range(BOARD_SIZE):
            ch = board[r][c]
            if r == lr and c == lc and ch in ('B', 'W'):
                ch = ch.lower()
            cells.append(ch)
        lines.append(f'{r + 1:>2}  ' + ' '.join(cells))

    return lines


# ---------- README 生成 ----------

def generate_readme(state, repo_name, stats):
    username = repo_name.split("/")[0]
    board = state['board']
    turn = state['turn']
    winner = state['winner']
    game_id = state.get('game_id', 1)
    move_count = state['move_count']
    last_move = state['last_move'] or '--'

    NEON    = '00F0FF'
    MAGENTA = 'FF00AA'
    GREEN   = '39FF14'
    PURPLE  = 'BD00FF'

    if winner:
        status_en = 'BLACK_WIN' if winner == 'B' else 'WHITE_WIN'
    else:
        status_en = 'BLACK_TURN' if turn == 'B' else 'WHITE_TURN'

    L = []

    # ========== 顶部 Banner ==========
    L += [
        '<div align="center">',
        '',
        f'<img src="https://capsule-render.vercel.app/api?type=waving'
        f'&color=0:{NEON},100:{PURPLE}&height=160&section=header'
        f'&text={username.upper()}&fontSize=48&fontColor=ffffff'
        f'&animation=fadeIn&fontAlignY=38" width="100%" />',
        '',
        f'<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono'
        f'&size=22&duration=3000&pause=800&color={NEON}&center=true'
        f'&vCenter=true&width=700'
        f'&lines=SYSTEM+ONLINE'
        f'%3BWELCOME+TO+Aoan2011%27S+PROFILE'
        f'%3BBUILDING+One-Editor+with+Textual'
        f'%3BFIVE-IN-A-ROW+ENGINE+RUNNING" />',
        '',
        '</div>',
    ]

    # ========== 主状态栏 ==========
    line1 = f"  GOMOKU ENGINE v1.0     STATUS: [ {status_en} ]"
    line2 = f"  GAME ID : {game_id:<6}   MOVE : {move_count:<6}   LAST : {last_move:<8}"
    line3 = "  FEATURED: One-Editor [ Textual TUI Editor ]"

    L += [
        '',
        '```text',
        '╔' + '═' * 62 + '╗',
        '║' + line1.ljust(62) + '║',
        '║' + line2.ljust(62) + '║',
        '╠' + '═' * 62 + '╣',
        '║' + line3.ljust(62) + '║',
        '╚' + '═' * 62 + '╝',
        '```',
        '',
    ]

    # ========== 面板 0：ASCII 棋盘 + 引导 ==========
    W = 62

    def row(text):
        return '║' + text.ljust(W) + '║'

    lr, lc = parse_coord(state.get('last_move'))
    has_last = lr >= 0 and lc >= 0

    board_view = []
    board_view.append('╔' + '═' * W + '╗')
    board_view.append(row('  ◤ BOARD ASCII VIEW ◢'))
    board_view.append(row(''))
    board_view.append(row('    [B] = Black   [W] = White   [.] = Empty'))
    if has_last:
        board_view.append(row('    [b] / [w] = LAST MOVE (highlighted)'))
    else:
        board_view.append(row('    (no moves yet)'))
    board_view.append(row(''))
    board_view.append('╠' + '═' * W + '╣')
    board_view.append(row(''))

    for line in render_board_ascii(board, state.get('last_move')):
        board_view.append(row(line.center(W)))

    # ---- 面板内引导（纯 ASCII，不破框） ----
    board_view.append(row(''))
    board_view.append('╠' + '═' * W + '╣')
    board_view.append(row(''))
    board_view.append(row('         >>>  SCROLL DOWN TO PLAY  <<<'.center(W)))
    board_view.append(row(''))
    board_view.append(row('      Click any [ . ] on the board below'.center(W)))
    board_view.append(row('      to place your stone'.center(W)))
    board_view.append(row(''))
    board_view.append('╚' + '═' * W + '╝')

    L += ['', '```text', *board_view, '```', '']

    # ========== 面板外引导（中文 + emoji，Markdown 引用块） ==========
    if winner:
        winner_name = '黑方 ⚫' if winner == 'B' else '白方 ⚪'
        L += [
            '<div align="center">',
            '',
            f'### 🏆 {winner_name} 获胜！',
            '',
            f'👉 [**点击这里开启新一局**](https://github.com/{repo_name}/issues/new'
            f'?title=gomoku%7Creset&body=点击Submit重置棋盘)',
            '',
            '</div>',
            '',
        ]
    else:
        turn_name = '黑方 ⚫' if turn == 'B' else '白方 ⚪'
        L += [
            '<div align="center">',
            '',
            f'### 👇 轮到 {turn_name} 落子 👇',
            '',
            '> 点击**下方棋盘**上的任意 `·`',
            '> → 自动创建 Issue',
            '> → 点 **Submit new issue**',
            '> → 30 秒后棋盘自动更新',
            '',
            '**棋盘坐标**：列 `A~O` × 行 `1~15`，例如 `H8` 表示第 8 行第 H 列',
            '',
            '</div>',
            '',
        ]

    # ========== 面板 A：当前局势 ==========
    black_count = sum(row_.count('B') for row_ in board)
    white_count = sum(row_.count('W') for row_ in board)
    total_stones = black_count + white_count

    game_moves = [m for m in stats.get('moves', []) if m.get('game') == game_id]
    last_five = list(reversed(game_moves[-5:]))

    players = {'B': None, 'W': None}
    for m in game_moves:
        c = m.get('color')
        if c in players and players[c] is None:
            players[c] = m.get('user')

    situ = []
    situ.append('╔' + '═' * W + '╗')
    situ.append(row('  ◤ CURRENT SITUATION ◢'))
    situ.append('╠' + '═' * W + '╣')
    situ.append(row(f'  BLACK [B] : {black_count:<3} stones     WHITE [W] : {white_count:<3} stones'))
    situ.append(row(f'  TOTAL     : {total_stones:<3} stones     TURN      : {status_en}'))
    situ.append('╠' + '═' * W + '╣')
    situ.append(row('  RECENT MOVES'))
    if last_five:
        for i, m in enumerate(last_five):
            move_no = len(game_moves) - i
            color_letter = m.get('color', '?')
            coord = m.get('coord', '--')
            user = m.get('user', 'unknown')
            tag = '  <- last' if i == 0 else ''
            if len(user) > 20:
                user = user[:17] + '...'
            situ.append(
                row(f'    {move_no:>3}.  {color_letter}  {coord:<4}  by {user:<20}{tag}')
            )
    else:
        situ.append(row('    (no moves yet)'))
    situ.append('╠' + '═' * W + '╣')
    situ.append(row('  PLAYERS'))
    bp = players.get('B') or '(waiting...)'
    wp = players.get('W') or '(waiting...)'
    if len(bp) > 40:
        bp = bp[:37] + '...'
    if len(wp) > 40:
        wp = wp[:37] + '...'
    situ.append(row(f'    [B]  {bp}'))
    situ.append(row(f'    [W]  {wp}'))
    situ.append('╚' + '═' * W + '╝')

    L += ['', '```text', *situ, '```', '']

    # ========== 面板 B：分析与战绩 ==========
    b3, b4 = scan_threats(board, 'B')
    w3, w4 = scan_threats(board, 'W')
    b_pct, w_pct = predict_win_rate(board)

    recent_games = get_recent_games(stats, n=3)
    active = get_active_players(stats, hours=24)

    analysis = []
    analysis.append('╔' + '═' * W + '╗')
    analysis.append(row('  ◤ ANALYSIS & HISTORY ◢'))
    analysis.append('╠' + '═' * W + '╣')
    analysis.append(row(f'  WIN RATE  : BLACK {b_pct:>3}%   |   WHITE {w_pct:>3}%'))
    analysis.append(row(f'  THREATS   : BLACK 3x{b3} 4x{b4}   |   WHITE 3x{w3} 4x{w4}'))
    analysis.append('╠' + '═' * W + '╣')
    analysis.append(row('  RECENT GAMES'))
    if recent_games:
        for g in recent_games:
            gid = g.get('id', '?')
            gw = g.get('winner', '?')
            gm = g.get('moves', '?')
            analysis.append(
                row(f'    Game #{gid:<3}   {gw} wins   in   {gm:<3} moves')
            )
    else:
        analysis.append(row('    (no completed games yet)'))
    analysis.append('╠' + '═' * W + '╣')
    analysis.append(row('  ACTIVE (last 24h)'))
    if active:
        for user, cnt in active:
            u = user if len(user) <= 30 else user[:27] + '...'
            analysis.append(row(f'    {u:<34}  {cnt:>2} moves'))
    else:
        analysis.append(row('    (no recent activity)'))
    analysis.append('╚' + '═' * W + '╝')

    L += ['', '```text', *analysis, '```', '']

    # ========== 精选项目：One-Editor ==========
    PROJECT = 'One-Editor'
    proj = 'https://img.shields.io/github'
    pin_card = (
        f'https://github-readme-stats.vercel.app/api/pin/'
        f'?username={username}&repo={PROJECT}'
        f'&theme=tokyonight&hide_border=true'
        f'&bg_color=0a0e14&title_color={NEON}'
        f'&icon_color={PURPLE}&text_color=c9d1d9'
    )

    L += [
        '---',
        '',
        '## ▸ FEATURED PROJECT',
        '',
        '<div align="center">',
        '',
        f'<a href="https://github.com/{username}/{PROJECT}">',
        f'<img src="{pin_card}" height="150" />',
        '</a>',
        '',
        f'<img src="{proj}/stars/{username}/{PROJECT}'
        f'?style=for-the-badge&color={NEON}&labelColor=0a0e14&logo=github" />',
        f'<img src="{proj}/forks/{username}/{PROJECT}'
        f'?style=for-the-badge&color={PURPLE}&labelColor=0a0e14&logo=git" />',
        f'<img src="{proj}/issues/{username}/{PROJECT}'
        f'?style=for-the-badge&color={MAGENTA}&labelColor=0a0e14&logo=githubactions" />',
        f'<img src="{proj}/last-commit/{username}/{PROJECT}'
        f'?style=for-the-badge&color={GREEN}&labelColor=0a0e14&logo=git" />',
        '',
        f'<img src="{proj}/languages/top/{username}/{PROJECT}'
        f'?style=for-the-badge&color={NEON}&labelColor=0a0e14" />',
        f'<img src="{proj}/repo-size/{username}/{PROJECT}'
        f'?style=for-the-badge&color={PURPLE}&labelColor=0a0e14" />',
        f'<img src="https://img.shields.io/badge/Textual-TUI-{NEON}'
        f'?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0e14" />',
        f'<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB'
        f'?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0e14" />',
        '',
        f'### [`{PROJECT}`](https://github.com/{username}/{PROJECT})',
        '',
        '> `TUI Editor` · Built with **Textual** · Python · 在终端里书写代码的全新方式',
        '',
        '</div>',
        '',
    ]

    # ========== 棋盘（Markdown 表格，可点击） ==========
    L += ['---', '', '## ▸ BOARD — CLICK TO PLAY', '']

    if winner:
        reset_url = (
            f'https://github.com/{repo_name}/issues/new'
            f'?title=gomoku%7Creset&body=点击Submit重置棋盘'
        )
        L += [
            f'### 🏆 **{NAME[winner]} WINS**',
            '',
            f'👉 [🔄 RESET BOARD]({reset_url})',
            '',
        ]
    else:
        L += [
            f'> 当前回合 **{NAME[turn]}** ｜ 点击下方任意 `·` 落子',
            '',
        ]

    header = '|   |' + '|'.join(
        f'**{chr(ord("A") + i)}**' for i in range(BOARD_SIZE)
    ) + '|'
    sep = '|:---:|' + ':---:|' * BOARD_SIZE
    L += [header, sep]

    for r in range(BOARD_SIZE):
        cells = [f'**{r + 1}**']
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            symbol = SYMBOL[cell]
            coord = f'{chr(ord("A") + c)}{r + 1}'
            if winner or cell != '.':
                cells.append(symbol)
            else:
                url = (
                    f'https://github.com/{repo_name}/issues/new'
                    f'?title=gomoku%7Cplace%7C{coord}&body=点击Submit落子'
                )
                cells.append(f'[{symbol}]({url})')
        L.append('|' + '|'.join(cells) + '|')

    # ========== 战绩图 ==========
    L += [
        '',
        '---',
        '',
        '## ▸ TELEMETRY',
        '',
        '<div align="center">',
        '',
        f'<img src="{CHART_FILE}" width="95%" />',
        '',
        '</div>',
        '',
    ]

    # ========== GitHub 数据 ==========
    stats_base = 'https://github-readme-stats.vercel.app/api'
    theme = 'tokyonight'
    L += [
        '---',
        '',
        '## ▸ GITHUB METRICS',
        '',
        '<div align="center">',
        '',
        f'<img height="165" src="{stats_base}?username={username}'
        f'&show_icons=true&theme={theme}&hide_border=true'
        f'&bg_color=0a0e14&title_color={NEON}&icon_color={PURPLE}&text_color=c9d1d9" />',
        f'<img height="165" src="{stats_base}/top-langs/?username={username}'
        f'&layout=compact&theme={theme}&hide_border=true'
        f'&bg_color=0a0e14&title_color={NEON}&text_color=c9d1d9" />',
        '',
        f'<img src="https://streak-stats.demolab.com?user={username}'
        f'&theme={theme}&hide_border=true&background=0a0e14'
        f'&ring={NEON}&fire={MAGENTA}&currStreakLabel={NEON}" />',
        '',
        f'<img src="https://github-profile-trophy.vercel.app/?username={username}'
        f'&theme={theme}&no-frame=true&no-bg=true&row=1&column=7&margin-w=8" />',
        '',
        f'<img src="https://github-readme-activity-graph.vercel.app/graph'
        f'?username={username}&theme=tokyo-night&hide_border=true'
        f'&bg_color=0a0e14&color={NEON}&line={MAGENTA}&point={GREEN}" width="95%" />',
        '',
        '</div>',
        '',
    ]

    # ========== 页脚 ==========
    L += [
        '---',
        '',
        '<div align="center">',
        '',
        f'<img src="https://visitor-badge.laobi.icu/badge'
        f'?page_id={repo_name}&color={NEON}&label=VISITORS" />',
        '',
        '`[ SYSTEM READY ]` `[ POWERED BY GITHUB ACTIONS ]` `[ © Aoan2011 ]`',
        '',
        '</div>',
    ]

    return '\n'.join(L)


def write_output(should_commit, message=''):
    out_path = os.environ.get('GITHUB_OUTPUT')
    if not out_path:
        return
    with open(out_path, 'a', encoding='utf-8') as f:
        f.write(f'commit={"true" if should_commit else "false"}\n')
        if message:
            clean = message.replace('\n', ' ').replace('%', '')
            f.write(f'message={clean}\n')


# ---------- 主流程 ----------

def main():
    repo_name = os.environ['GITHUB_REPOSITORY']
    issue_title = os.environ.get('ISSUE_TITLE', '').strip()
    issue_number = os.environ.get('ISSUE_NUMBER')
    issue_user = os.environ.get('ISSUE_USER', 'unknown')

    state = load_json(STATE_FILE, fresh_state())
    stats = load_json(STATS_FILE, {'games': [], 'moves': []})

    if not issue_title:
        readme = generate_readme(state, repo_name, stats)
        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(readme)
        generate_chart(STATS_FILE, STATE_FILE, CHART_FILE)
        write_output(True, 'Regenerate README and chart [skip ci]')
        return

    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(int(issue_number))

    should_commit = False
    commit_msg = ''

    if issue_title.startswith('gomoku|reset'):
        old_id = state.get('game_id', 1)
        state = fresh_state(game_id=old_id + 1)
        comment = '🔄 棋盘已重置，黑方先行。'
        should_commit = True
        commit_msg = f'Reset board to game #{state["game_id"]} [skip ci]'

    else:
        match = re.match(r'gomoku\|place\|([A-O])(\d{1,2})$', issue_title)
        if not match:
            issue.create_comment('❌ 无效指令。请通过点击棋盘落子。')
            issue.edit(state='closed')
            write_output(False)
            return

        col = ord(match.group(1)) - ord('A')
        row = int(match.group(2)) - 1
        coord = f'{match.group(1)}{match.group(2)}'

        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            issue.create_comment('❌ 坐标超出棋盘范围。')
            issue.edit(state='closed')
            write_output(False)
            return

        if state['winner']:
            issue.create_comment('❌ 游戏已结束，请先重置棋盘。')
            issue.edit(state='closed')
            write_output(False)
            return

        if state['board'][row][col] != '.':
            issue.create_comment(f'❌ 位置 {coord} 已有棋子。')
            issue.edit(state='closed')
            write_output(False)
            return

        color = state['turn']
        board = [list(r) for r in state['board']]
        board[row][col] = color
        state['board'] = [''.join(r) for r in board]
        state['last_move'] = coord
        state['move_count'] += 1

        stats['moves'].append({
            'game': state.get('game_id', 1),
            'coord': coord,
            'color': color,
            'user': issue_user,
            'time': datetime.now(timezone.utc).isoformat(),
        })

        if check_win(board, row, col, color):
            state['winner'] = color
            comment = f'🏆 {NAME[color]} 落子 {coord}，五子连珠获胜！'
            if not state.get('recorded'):
                stats['games'].append({
                    'id': state.get('game_id', 1),
                    'winner': color,
                    'moves': state['move_count'],
                    'players': sorted({
                        m['user'] for m in stats['moves']
                        if m.get('game') == state.get('game_id', 1)
                    }),
                })
                state['recorded'] = True
        else:
            state['turn'] = 'W' if color == 'B' else 'B'
            comment = f'✅ {NAME[color]} 落子 {coord}，轮到 {NAME[state["turn"]]}。'

        should_commit = True
        commit_msg = f'Move {coord} by {issue_user} [skip ci]'

    save_json(STATE_FILE, state)
    save_json(STATS_FILE, stats)

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(generate_readme(state, repo_name, stats))

    generate_chart(STATS_FILE, STATE_FILE, CHART_FILE)

    issue.create_comment(comment)
    issue.edit(state='closed')

    write_output(should_commit, commit_msg)


if __name__ == '__main__':
    main()
