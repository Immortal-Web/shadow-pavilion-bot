import os
import tempfile
import unittest

import db
from constants import TABLE_GEN, TNAME_INDEX, TREGEX_INDEX
import re


class SqlstrTests(unittest.TestCase):
    def test_quotes_plain_value(self):
        self.assertEqual(db.sqlstr("bob"), "'bob'")

    def test_doubles_embedded_quotes(self):
        self.assertEqual(db.sqlstr("it's"), "'it''s'")

    def test_none_becomes_sql_null(self):
        self.assertEqual(db.sqlstr(None), "NULL")

    def test_numbers_get_stringified(self):
        self.assertEqual(db.sqlstr(123), "'123'")


class EasyStrTests(unittest.TestCase):
    def test_user_str_escapes_and_nulls(self):
        s = db.easy_user_str(123, "it's bob", None)
        self.assertEqual(s, "('123','it''s bob',NULL)")

    def test_built_values_pass_their_tables_regex(self):
        # the whole house of cards: whatever we build must clear TABLE_GEN's regex
        for values, table_name in [
            (db.easy_user_str(1, "it's", None), "Users"),
            (db.easy_nickn_str(1, "it's"), "Nicknames"),
            (db.easy_expln_str(5, "he's the man"), "Explanations"),
        ]:
            regex = next(t[TREGEX_INDEX] for t in TABLE_GEN if t[TNAME_INDEX] == table_name)
            self.assertIsNotNone(re.search(regex, values), f"{values} rejected by {table_name} regex")


class AddRecordTests(unittest.TestCase):
    def test_apostrophe_nickname_actually_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            self.assertTrue(daba.addRecord("Users", db.easy_user_str(123, "bob", "Bob")))
            self.assertTrue(daba.addRecord("Nicknames", db.easy_nickn_str(123, "it's bob")))
            rows = daba.rdRecords("Nicknames", "nickname", "WHERE user_id = '123'")
            self.assertEqual(rows, [("it's bob",)])
            daba.finish()  #windows won't delete the temp file while the connection is open

    def test_garbage_values_return_false_instead_of_silent_print(self):
        with tempfile.TemporaryDirectory() as tmp:
            daba = db.dbthingy(os.path.join(tmp, "t.db"))
            daba.SetupDB()
            self.assertFalse(daba.addRecord("Users", "('1','2')"))          # wrong shape
            self.assertFalse(daba.addRecord("Nonsense", "('a','b','c')"))   # no such table
            daba.finish()


if __name__ == "__main__":
    unittest.main()
