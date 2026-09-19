import os
import tempfile
import unittest

import db


class FreshSchemaTests(unittest.TestCase):
    def test_new_nickname_gets_a_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.addRecord("Users", db.easy_user_str(1, "bob", "Bob"))
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "nick"))
            rows = daba.rdRecords("Nicknames", "nickname, changed_at", "WHERE user_id = '1'")
            self.assertEqual(rows[0][0], "nick")
            self.assertIsNotNone(rows[0][1])  # datetime('now') fired
            daba.finish()

    def test_index_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            idx = [r[1] for r in daba.cnctn.execute("PRAGMA index_list(Nicknames)").fetchall()]
            self.assertIn("idx_nicknames_user_id", idx)
            daba.finish()


#what the Nicknames table looked like before timestamps existed
LEGACY_NICKN_SQL = """
                    CREATE TABLE Nicknames(
                        nickn_id INTEGER PRIMARY KEY,
                        user_id varchar(35),
                        nickname varchar(35),
                        FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    );
                """


class MigrationTests(unittest.TestCase):
    def test_old_db_gets_changed_at_added_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            #rewind Nicknames to the pre-timestamp shape, with one old row in it
            daba.crsr.execute("DROP TABLE Nicknames")
            daba.crsr.execute(LEGACY_NICKN_SQL)
            daba.cnctn.commit()
            daba.addRecord("Users", db.easy_user_str(1, "old", "Old"))
            daba.crsr.execute("INSERT INTO Nicknames VALUES (NULL,'1','ancient nick')")
            daba.cnctn.commit()

            daba.SetupDB()  #should notice and migrate, not explode

            old_rows = daba.rdRecords("Nicknames", "nickname, changed_at", "WHERE nickname = 'ancient nick'")
            self.assertEqual(old_rows[0][0], "ancient nick")  #data survived
            self.assertIsNone(old_rows[0][1])                 #we don't know when it was set, and that's honest
            daba.addRecord("Nicknames", db.easy_nickn_str(1, "new nick"))
            new_rows = daba.rdRecords("Nicknames", "changed_at", "WHERE nickname = 'new nick'")
            self.assertIsNotNone(new_rows[0][0])              #new rows do get stamped
            daba.finish()

    def test_setupdb_is_idempotent_on_new_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            daba.SetupDB()  #second run: column already there, must not try to add it again
            daba.addRecord("Users", db.easy_user_str(1, "a", "A"))
            rows = daba.rdRecords("Users", "username", "")
            self.assertEqual(rows, [("a",)])
            daba.finish()


if __name__ == "__main__":
    unittest.main()
