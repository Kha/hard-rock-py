import socket
import json
import sys
import os
import functools

from Vec2d import Vec2d
v = Vec2d

class Client:
    HOST = os.environ.get('HRR_HOST', '127.0.0.1')
    PORT = 1993
    BUF_SIZE = 100

    def __init__(self):
        self._received = ""

    def connect(self, handshake):
        self._s = socket.socket()
        self._s.connect((Client.HOST, Client.PORT))
        self.send(handshake)
        assert(self.recv()['status'] == True)

    def send(self, obj):
        data = json.dumps(obj) + "\n"
        self._s.send(data.encode('utf-8'))

    def recv(self):
        while not "\n" in self._received:
            received = self._s.recv(Client.BUF_SIZE).decode('utf-8')
            if received == "":
                raise Exception('Server shut down')
            self._received += received

        [obj, self._received] = self._received.split("\n", 1)
        return json.loads(obj)

class Observer(Client):
    def connect(self):
        super().connect({"message":"connect", "type":"observer"})

class Direction:
    UP = v(0, -1)
    RIGHT = v(1, 0)
    DOWN = v(0, 1)
    LEFT = v(-1, 0)

    assert(UP.perpendicular() == RIGHT)

class Tile:
    SEGMENT_SIZE = 45
    TRACK_WIDTH = 5 * SEGMENT_SIZE

    def __init__(self, pos, dir_in):
        self.pos = pos
        self.dir_in = dir_in

    @staticmethod
    def create(type, pos, dir_in):
        return {"straight": StraightTile, "finish": FinishTile,
                "turnleft": functools.partial(TurnTile, TurnTile.LEFT),
                "turnright": functools.partial(TurnTile, TurnTile.RIGHT)
               }[type](pos, dir_in)

class StraightTile(Tile):
    @property
    def dir_out(self): return self.dir_in

    @property
    def size(self):
        diag = v(Tile.SEGMENT_SIZE, Tile.TRACK_WIDTH) * self.dir_in
        return v(abs(diag.x), abs(diag.y))

class TurnTile(Tile):
    LEFT = object()
    RIGHT = object()

    def __init__(self, type, pos, dir_in):
        super().__init__(pos, dir_in)
        self.type = type

    @property
    def dir_out(self):
        out = self.dir_in.perpendicular()
        if type == TurnTile.LEFT: out = -out
        return out

    @property
    def size(self):
        return v(6 * Tile.TRACK_WIDTH, 6 * Tile.TRACK_WIDTH)

class FinishTile(StraightTile): pass

class Track:
    def __init__(self, msg):
        assert(msg['message'] == "track")
        self.width = msg['width']
        self.height = msg['height']
        self.startdir = getattr(Direction, msg['startdir'])
        if msg['tiled']:
            self.tiles = []
            dir_in = self.startdir
            for [type, x, y] in msg['tiles']:
                self.tiles.append(Tile.create(type, v(x, y), dir_in))
                dir_in = self.tiles[-1].dir_out
        else:
            self.data = [[msg['data'][x + self.width * y] for x in range(self.width)] for y in range(self.height)]

class Player(Client):
    def __init__(self, name):
        super().__init__()
        self._name = name

    def connect(self, character, cartype, tracktiled=True):
        super().connect({"message":"connect", "type":"player", "name":self._name, "character":character, "cartype":cartype, "tracktiled":tracktiled})
        while True:
            self.dispatch()

    def dispatch(self):
        obj = self.recv()
        message = obj['message']
        del obj['message']

        try:
            getattr(self, message)(**obj)
        except AttributeError:
            print("WARN: unhandled message {}".format(message))

    def do(self, action):
        self.send({"message":"action", "type":action})

    # messages

    def gamestart(self, players, laps, track):
        self.players = players
        self.laps = laps
        self.track = Track(track)

    def action(self, type, player): pass

    def gamestate(self, time, cars, missiles, mines):
        self.time = time
        self.cars = cars
        self.missiles = missiles
        self.mines = mines
        self.tick()

    def tick(self): pass
