#!/usr/bin/env python3
from libqtile.layout.base import Layout, _ClientList
from libqtile import layout

# Implement swap functionality in Columns layout
class Column(_ClientList):
    # shortcuts for current client and index used in Columns layout
    cw = _ClientList.current_client
    current = _ClientList.current_index

    def __init__(self, split, insert_position, width=100):
        super().__init__()
        self.width = width
        self.split = split
        self.insert_position = insert_position
        self.heights = {}

    def info(self):
        info = _ClientList.info(self)
        info.update(
            dict(
                heights=[self.heights[c] for c in self.clients],
                split=self.split,
            )
        )
        return info

    def toggle_split(self):
        self.split = not self.split

    def update_height(self, client, height):
        self.heights[client] = height
        delta = 100 - height
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def add(self, client, height=100):
        _ClientList.add(self, client, self.insert_position)
        self.update_height(client,height)

    def add_to_tail(self, client, current=True, height=100):
        self.clients.append(client)
        if current:
            self.current_client = client
        self.update_height(client, height)

    def place(self, client, height, pos, current=True):
        self.clients.insert(pos, client)
        if current: self.current_client = client
        self.update_height(client, height)

    def remove(self, client):
        _ClientList.remove(self, client)
        delta = self.heights[client] - 100
        del self.heights[client]
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def __str__(self):
        cur = self.current
        return "Column: " + ", ".join(
            [
                "[%s: %d]" % (c.name, self.heights[c])
                if c == cur
                else "%s: %d" % (c.name, self.heights[c])
                for c in self.clients
            ]
        )

class OmniLayout(layout.Columns):
    def __init__(self, autotile=True, automove=True, max_stack=3, labels=True, **config):
        Layout.__init__(self, **config)
        self.add_defaults(layout.Columns.defaults)
        self.columns = [Column(self.split, self.insert_position)]
        self.name = "Omni"
        self.current = 0
        self.autotile = autotile
        self.automove = automove
        self.max_stack = max_stack

    def clone(self, group):
        c = Layout.clone(self, group)
        c.columns = [Column(self.split, self.insert_position)]
        return c

    def add_column(self, prepend=False):
        c = Column(self.split, self.insert_position)
        if prepend:
            self.columns.insert(0, c)
            self.current += 1
        else:
            self.columns.append(c)
        return c

    def add(self, client, current=True):
        c = self.cc
        condition1 = len(c) > 0 and len(self.columns) < self.num_columns
        condition2 = self.autotile and (len(self.columns) > 1 and len(self.columns[-1]) >= self.max_stack)
        if condition1 or condition2:
            c = self.add_column()
        elif self.fair:
            least = min(self.columns, key=len)
            if len(least) < len(c):
                c = least
        elif self.autotile:
            c = self.columns[-1]

        self.current = self.columns.index(c)

        c.add_to_tail(client,current=current) if self.autotile else c.add(client)

    def remove(self, client):
        remove = None
        for c in self.columns:
            if client in c:
                c.remove(client)
                if len(c) == 0 and len(self.columns) > 1:
                    remove = c
                break
        # Automove windows when there are less windows than max stack config
        removed = None
        if remove is not None:
            removed = self.columns.index(remove)
            self.remove_column(remove)
        if self.automove and self.autotile:
            self.adjust_clients(self.current, removed)

        return self.columns[self.current].cw

    def adjust_clients(self, ccidx, removed = None):
        collen = len(self.columns)
        currentcol = self.columns[ccidx]
        regadjust = len(currentcol) < self.max_stack and ccidx+1 != collen
        if regadjust and ccidx != 0:
            for c in self.columns[ccidx:-1]:
                if len(c) < self.max_stack:
                    nexti = self.columns.index(c) + 1
                    nextc = self.columns[nexti]
                    win = nextc.focus_first()
                    nextc.remove(win)
                    c.add_to_tail(win, current=False)
        elif removed == 0:
            top = self.cc.focus_first()
            self.cc.remove(top)
            self.add_column(prepend=True).add_to_tail(top,current=True)
            self.current = 0
            if collen > 1 and len(self.columns[1]) < self.max_stack:
                self.adjust_clients(1)

        if len(self.columns[-1]) == 0:
            self.remove_column(self.columns[-1])

    def focus_next(self, win):
        """Returns the next client after 'win' in layout,
        or None if there is no such client"""
        # First: try to get next window in column of win (self.columns is non-empty)
        # pylint: disable=undefined-loop-variable
        for idx, col in enumerate(self.columns):
            if win in col:
                nxt = col.focus_next(win)
                if nxt:
                    return nxt
                else:
                    break
        # if there was no next, get first client from next column
        collen, ccidx = len(self.columns), self.columns.index(self.cc)
        if collen > 1:
            idx = 0 if ccidx + 1 == collen else ccidx + 1
            return self.columns[idx].focus_first()

    def focus_previous(self, win):
        """Returns the client previous to 'win' in layout.
        or None if there is no such client"""
        # First: try to focus previous client in column (self.columns is non-empty)
        # pylint: disable=undefined-loop-variable
        for idx, col in enumerate(self.columns):
            if win in col:
                prev = col.focus_previous(win)
                if prev:
                    return prev
                else:
                    break
        # If there was no previous, get last from previous column
        if len(self.columns) > 1:
            idx = self.columns.index(self.cc)
            return self.columns[idx - 1].focus_last()

    def swap(self, window1, window2):
        """Swap two windows"""
        w1colidx = self.current
        w2colidx = 0
        for i, col in enumerate(self.columns):
            if window2 in col:
                w2colidx = i
                break
        if w1colidx == w2colidx:
            h1, h2 = self.cc.heights[window2], self.cc.heights[window1]
            self.cc.heights[window1], self.cc.heights[window2] = h1, h2
            self.cc.swap(window1, window2, 1)
        else:
            w1col, w2col = self.columns[w1colidx], self.columns[w2colidx]
            h2, h1 = w2col.heights[window2], w1col.heights[window1]
            i1, i2 = w1col.index(window1), w2col.index(window2)
            w1col.remove(window1)
            w2col.place(window1,h2,i2)
            w2col.remove(window2)
            w1col.place(window2,h1,i1)
            if self.current < w2colidx:
                self.current += 1
            else:
                self.current -= 1
        self.group.layout_all()
        self.group.focus(window1)

    def get_largest(self):
        rated_clients = []
        for col in self.columns:
            for c, h in col.heights.items():
                rated_clients.append({"client":c,"rating":(col.width / len(col)) + h})
        return max(rated_clients, key=lambda x: x["rating"])["client"]


    def cmd_swap_to_largest(self):
        win = self.cc.cw
        target = self.get_largest()
        if win != target and win and target:
            self.swap(win, target)

    def cmd_swap_down(self):
        """Swap current window with closest window to the down"""
        win = self.cc.cw
        target = self.focus_next(win)
        if win and target:
            self.swap(win, target)

    def cmd_swap_up(self):
        """Swap current window with closest window to the up"""
        win = self.cc.cw
        target = self.focus_previous(win)
        if win and target:
            self.swap(win, target)

    def cmd_swap_right(self):
        collen, ccidx = len(self.columns), self.columns.index(self.cc)
        if collen > 1:
            if ccidx + 1 == collen:
                idx = 0
            else:
                idx = ccidx + 1
            win = self.cc.cw
            target = self.columns[idx].focus_first()
            self.swap(win,target)

    def cmd_swap_left(self):
        collen, ccidx = len(self.columns), self.columns.index(self.cc)
        if collen > 1:
            idx = ccidx - 1
            win = self.cc.cw
            target = self.columns[idx].focus_first()
            self.swap(win,target)

    def cmd_toggle_autotile(self):
        self.autotile = not self.autotile

    def cmd_toggle_automove(self):
        self.automove = not self.automove

    def cmd_inc_maxstack(self):
        self.max_stack += 1

    def cmd_dec_maxstack(self):
        self.max_stack -= 1

    def cmd_reset(self):
        clients = []
        for col in self.columns:
            for cl in col:
                clients.append(cl)
                col.remove(cl)
                if len(col) == 0:
                    self.remove_column(col)
        if clients:
            self.current = 0
            for cl in clients:
                self.add(cl)
            self.cc.focus(self.cc.focus_first())
            self.cmd_normalize()

