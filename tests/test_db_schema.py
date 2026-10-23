import os
import sqlite3
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

    def test_reused_nickname_keeps_its_original_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
            daba.addRecord("Users", db.easy_user_str(2, "b", "B"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "old"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "new"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "old"))
            daba.addRecord("Nicknames", db.easy_nickn_str(2, "old"))
            self.assertEqual(daba.rdRecords("Nicknames", "nickn_id, user_id, nickname", "ORDER BY nickn_id"),
                             [(1, "1", "old"), (2, "1", "new"), (3, "2", "old")])
            #the database enforces this too, even if a caller bypasses addRecord
            with self.assertRaises(sqlite3.IntegrityError):
                daba.cnctn.execute("INSERT INTO Nicknames VALUES (NULL, '1', 'old')")
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


class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.daba = db.dbthingy(os.path.join(self.tmp.name, "legacy.db"))
        self.addCleanup(self.daba.finish)
        #the old schema has no unique index; build it without running the migration
        for table in db.TABLE_GEN:
            self.daba.cnctn.execute(table[db.TSQL_INDEX])
        self.daba.cnctn.executescript("""
            INSERT INTO Users VALUES ('1', 'a', 'A'), ('2', 'b', 'B');
            INSERT INTO Nicknames VALUES
                (4, '1', 'it''s old'), (8, '1', 'new'),
                (9, '1', 'it''s old'), (12, '1', 'it''s old'), (15, '2', 'it''s old');
            INSERT INTO Explanations VALUES
                (1, 4, 'original'), (2, 9, 'second'), (3, 12, 'third'), (4, 15, 'other user');
        """)

    def test_migration_keeps_oldest_ids_and_every_explanation(self):
        self.daba.SetupDB()
        self.daba.SetupDB()  #safe on later boots too
        self.assertEqual(self.daba.rdRecords("Nicknames", "*", "ORDER BY nickn_id"),
                         [(4, "1", "it's old"), (8, "1", "new"), (15, "2", "it's old")])
        self.assertEqual(self.daba.rdRecords("Explanations", "*", "ORDER BY expln_id"),
                         [(1, 4, "original"), (2, 4, "second"), (3, 4, "third"), (4, 15, "other user")])
        self.assertEqual(self.daba.cnctn.execute("PRAGMA foreign_key_check").fetchall(), [])
        with self.assertRaises(sqlite3.IntegrityError):
            self.daba.cnctn.execute("INSERT INTO Nicknames VALUES (NULL, '1', 'it''s old')")

    def test_failed_migration_rolls_back_explanation_moves_and_deletes(self):
        before_nicks = self.daba.rdRecords("Nicknames", "*", "ORDER BY nickn_id")
        before_expls = self.daba.rdRecords("Explanations", "*", "ORDER BY expln_id")
        self.daba.cnctn.execute("""
            CREATE TRIGGER fail_delete BEFORE DELETE ON Nicknames
            BEGIN SELECT RAISE(ABORT, 'test failure'); END;
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.daba.SetupDB()
        self.assertEqual(self.daba.rdRecords("Nicknames", "*", "ORDER BY nickn_id"), before_nicks)
        self.assertEqual(self.daba.rdRecords("Explanations", "*", "ORDER BY expln_id"), before_expls)


if __name__ == "__main__":
    unittest.main()
