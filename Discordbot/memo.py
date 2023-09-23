import lmdb
from dataclasses import dataclass, asdict, field
import cbor2
import datetime
from pdb import set_trace

def now() -> int:
    return int(datetime.datetime.utcnow().timestamp() * 1000)
    # return int(time.time())

@dataclass
class Record:
    protocol: str # discord|nostr
    channel: str # Disco 1154533165935902810, Nostr: note91230AF
    uid: str # Disco: 230361085889347584, Nostr: npubEEFF00AA
    author: str
    role: str # = field(default='user')
    content: str
    date: int = field(default_factory=now)

    def __post_init__(self):
        # self.channel = str(self.channel)
        # self.uid = str(self.uid)
        # self.author = str(self.author)
        # self.role = str(self.role)
        # self.content = str(self.content)
        pass

    def to_cbor(self):
        return cbor2.dumps(asdict(self))
    @staticmethod
    def from_cbor(buf):
        return Record(**cbor2.loads(buf))

class MemoRepo:
    def __init__(self, path):
        self.env = lmdb.open(path, max_dbs=10)
        self.chan_db = self.env.open_db(bytes('channels', 'utf8'))
        self.peers_db = self.env.open_db(bytes('people', 'utf8'))

    def append(self, record: Record):
        with self.env.begin(db=self.chan_db, write=True) as txn:
            key = MemoRepo.mk_key(record.protocol, record.channel, record.date)
            txn.put(key, record.to_cbor())

    def get_channel(self, protocol, channel, limit = 512):
        messages = []
        count = 0
        with self.env.begin(db=self.chan_db) as txn:
            cursor = txn.cursor()
            cursor.set_key(MemoRepo.mk_key(protocol, channel, now()))
            for k, v in cursor.iterprev():
                record = Record.from_cbor(v)
                count += len(record.content)
                if count >= limit: break
                if record.channel != channel: break
                messages.insert(0, record)
        return messages

    def set_user(self, protocol: str, uid: str, desc: str):
        with self.env.begin(db=self.peers_db, write=True) as txn:
            txn.put(bytes(f"{protocol}¤{uid}", "utf8"), cbor2.dumps(desc))

    def get_user(self, protocol: str, uid: str):
        with self.env.begin(db=self.peers_db) as txn:
            res = txn.get(bytes(f"{protocol}¤{uid}", "utf8"))
            if (res is not None): return cbor2.loads(res)
            return None

    @staticmethod
    def mk_key(proto, chan, date):
        return bytes(f"{proto}¤{chan}¤{date}", 'utf8')


if __name__ == '__main__':
    print("""
        .  .            _
        |\/| _ ._ _  _ |_) _ ._  _
        |  |(/_| | |(_)| \(/_|_)(_)
        Tests                |
    """)
    import unittest
    import os
    from shutil import rmtree
    DB_FILE = '.test_db'
    # Start fresh
    if os.path.exists(DB_FILE):
        rmtree(DB_FILE)
    db = MemoRepo('.test.lmdb')
    class TestConvoDB(unittest.TestCase):
        def test_1(self):
            cid = 20
            db.append(Record('discord', cid, 7, "telamohn", 'user', "a"))
            db.append(Record('discord', cid, 0, "Alice", 'assistant', "b"))
            db.append(Record('discord', cid, 7, "telamohn", 'user', "c"))
            messages = db.get_channel('discord', cid)
            self.assertEqual(len(messages), 3)
            msg = messages[0]
            self.assertEqual(msg.role, 'user')
            self.assertEqual(msg.content, 'a')

            # Test multi-channel
            cid = 21
            db.append(Record('discord', cid, 0, "Cat", 'user', "meow"))
            messages = db.get_channel('discord', cid)
            self.assertEqual(len(messages), 1)
            msg = messages[0]
            self.assertEqual(msg.role, 'user')
            self.assertEqual(msg.content, 'meow')

        def test_2_whois(self):
            db.get_user(7, "Describe [user] in a single line")
            self.assertEquals(db.set_user(7), "Describe [user] in a single line")

    unittest.main()
