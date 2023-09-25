import lmdb
from dataclasses import dataclass, asdict, field
import cbor2
import datetime
import tiktoken

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
    flag: int = field(default=0) # -1 Banned, 0 Unknown, +1 Approved

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

token_encoder = tiktoken.get_encoding("cl100k_base")
def to_tokens(text: str):
    return token_encoder.encode(text)
def count_tokens(text: str):
    return len(to_tokens(text))

class MemoRepo:
    def __init__(self, path):
        self.env = lmdb.open(path, max_dbs=10)

        self.chan_db = self.env.open_db('channels'.encode('utf8'))
        self.peers_db = self.env.open_db('people'.encode('utf8'))
        self.db_txt = self.env.open_db('txt'.encode('utf8'))

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
                count += count_tokens(record.content)
                if count >= limit: break
                if record.channel != channel: break
                messages.insert(0, record)
        return messages

    def set_user(self, protocol: str, uid: str, desc: str, **kwargs):
        with self.env.begin(db=self.peers_db, write=True) as txn:
            name = kwargs.get('name')
            key = f"o|{protocol}|{uid}".encode('utf8')
            txn.put(key, cbor2.dumps(desc))
            # Optionally index user by name
            if (name is not None):
                txn.put(f"a|{name.lower()}".encode('utf8'), key)

    def get_user(self, protocol: str, uid: str):
        with self.env.begin(db=self.peers_db) as txn:
            res = txn.get(bytes(f"o|{protocol}|{uid}", "utf8"))
            if (res is not None): return cbor2.loads(res)
            return None

    def search_user(self, protocol: str, q: str):
        query = str(q)
        # Find by UID
        out = self.get_user(protocol, query)
        if out is not None: return out

        # Peform name index lookup
        with self.env.begin(db=self.peers_db) as txn:
            name = query.lower()
            cursor = txn.cursor()
            cursor.set_range(f"a|{name}|".encode('utf8'))
            for k, ptr in cursor.iterprev():
                if name in k.decode('utf8'):
                    # Follow pointer
                    out = txn.get(ptr)
                    if out is not None: out = cbor2.loads(out)
        return out

    def set_txt(self, path, data):
        with self.env.begin(db=self.db_txt, write=True) as txn:
            txn.put(path.encode('utf8'), cbor2.dumps(data))

    def get_txt(self, path):
        with self.env.begin(db=self.db_txt) as txn:
            data = txn.get(path.encode('utf8'))
            if data is None:
                return 'error: File not found'
            return cbor2.loads(data)

    def list_txts(self):
        keys = []
        with self.env.begin(db=self.db_txt) as txn:
            cursor = txn.cursor()
            for k in cursor.iternext(values=False):
                keys.append(k.decode('utf8'))

        return '\n'.join(keys)

    def close (self):
        self.env.close()

    def clear (self):
        databases = [
            self.chan_db,
            self.peers_db
        ]
        with self.env.begin(write=True) as txn:
            for db in databases:
                txn.drop(db)
        self.env.sync(True)

    @staticmethod
    def mk_key(proto, chan, date):
        return bytes(f"{proto}|{chan}|{date}", 'utf8')


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

    # TODO: this failed
    # Workaround: rm -rf .test.lmdb/ && python memo.py
    # Start fresh
    # if os.path.exists(DB_FILE):
        # rmtree(DB_FILE)

    db = MemoRepo('.test.lmdb')
    class TestConvoDB(unittest.TestCase):
        # TODO: causes transactions to glitch
        # @classmethod
        # def setUpClass(cls):
        #     # db.clear()

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
            # num-keys
            db.set_user('n', 7, "A")
            self.assertEqual(db.get_user('n', 7), "A")
            # str-keys
            db.set_user('n', '23', 'B', name = 'tel')
            self.assertEqual(db.get_user('n', '23'), 'B')
            self.assertEqual(db.search_user('n', 7), 'A')
            self.assertEqual(db.search_user('n', 23), 'B')
            # fuzzy-search
            self.assertEqual(db.search_user('n', 'te'), 'B')

        def test_3_vfs(self):
            db.set_txt('/users/readme.txt', 'Placeholder')
            self.assertEqual(db.get_txt('/users/readme.txt'), "Placeholder")
            files = db.list_txts().split('\n')
            self.assertTrue('/users/readme.txt' in files)

    unittest.main()
