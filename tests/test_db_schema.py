import os
import tempfile
import unittest

import db


class FreshSchemaTests(unittest.TestCase):
    def test_nicknames_columns_are_exactly_upstreams(self):
        #nickn_id, user_id, nickname — nothing like a changed_at bolted on the end
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            cols = [r[1] for r in daba.cnctn.execute("PRAGMA table_info(Nicknames)").fetchall()]
            self.assertEqual(cols, ["nickn_id", "user_id", "nickname"])
            daba.finish()

    def test_nicknames_has_no_extra_index(self):
        #upstream never made one; INTEGER PRIMARY KEY is the rowid so none is auto-made either
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            idx = [r[1] for r in daba.cnctn.execute("PRAGMA index_list(Nicknames)").fetchall()]
            self.assertEqual(idx, [])
            daba.finish()

    def test_new_nickname_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.addRecord("Users", db.easy_user_str(1, "bob", "Bob"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "nick"))
            rows = daba.rdRecords("Nicknames", "user_id, nickname", "WHERE user_id = '1'")
            self.assertEqual(rows, [("1", "nick")])
            daba.finish()

    def test_setupdb_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.SetupDB()  #CREATE IF NOT EXISTS: running it again must be a no-op, not an explosion
            daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
            rows = daba.rdRecords("Users", "username", "")
            self.assertEqual(rows, [("a",)])
            daba.finish()


if __name__ == "__main__":
    unittest.main()
