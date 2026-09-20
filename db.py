
import sqlite3
import re
from constants import * #I think this is how its done??
#having used sqlalchemy, I can now say for sure: it sucks ass. my solution still sucks thou


# my "#define"s
gener_INSERT:str = "INSERT INTO {table} VALUES {values};"
gener_INSERT_IGNORE:str = "INSERT OR IGNORE INTO {table} VALUES {values};"
gener_UPDATE:str = "UPDATE {table} SET {changed} WHERE {conditions};"
gener_DELETE:str = "DELETE FROM {table} WHERE {conditions};"
gener_SELECT:str = "SELECT {csvalues} FROM {table} {conditions};"

#simple condition you can slap into {conditions} that should work for nearly everything?
gener_CONDITION:str = "{values} {operation} {condition}"
#for anything more complex just make unholy concactenations of 
#gener_SELECT(value, table, gener_CONDITION(value, "IN(" , gener_SELECT(...)))


class dbthingy:
    cnctn:sqlite3.Connection
    crsr: sqlite3.Cursor

    #autoconnects (that should be fine?)
    def __init__(self, db):
        self.cnctn=sqlite3.connect(db)
        self.cnctn.execute("PRAGMA foreign_keys = ON;")

        self.crsr = self.cnctn.cursor()

    def finish(self):
        self.cnctn.commit()
        self.cnctn.close()
        #this should be good enough I think?

    def save(self):
        #like finish() but doesn't close the connection (for batched inserts)
        self.cnctn.commit()

    #sets up the username database. intended to only be run once on initial setup,
    #but its not like running it again causes any problems
    def SetupDB(self):
        #apparently sqlite doesn't need a 'create database' command
        for tables in TABLE_GEN:
            self.crsr.execute(tables[TSQL_INDEX]) 

        #migration for dbs older than timestamp tracking: sqlite refuses ALTER ... ADD COLUMN
        #with a non-constant default, so add it plain. old rows stay NULL (we genuinely don't
        #know when they were set) and every new insert supplies datetime('now') itself
        cols = [row[1] for row in self.crsr.execute("PRAGMA table_info(Nicknames)").fetchall()]
        if "changed_at" not in cols:
            self.crsr.execute("ALTER TABLE Nicknames ADD COLUMN changed_at TEXT")

        self.crsr.execute(NICKN_INDEX_SQLCOM)
        self.cnctn.commit()

    #man honestly I miss the {} they actually make things easier to read
    
    #adds a record to the database. format: name, '(<csv>)' <--as you would if you were typing the sql yourself
    #one at a time i'm not processing multiple lmao
    def addRecord(self,tableName:str, addingvalues:str, ignoredupes:bool=False, commit:bool=True)->bool:
        #ignoredupes: swap INSERT for INSERT OR IGNORE (firstrun re-scans would otherwise
        #explode on the Users primary key). commit=False: caller batches and calls save() themselves
        succed:bool =False

        for table in TABLE_GEN:
            #checks for valid table name and values that match the table
            if tableName == table[TNAME_INDEX] and (re.search(table[TREGEX_INDEX],addingvalues))!= None:
                gener = gener_INSERT_IGNORE if ignoredupes else gener_INSERT
                self.crsr.execute(gener.format(table=tableName,values=addingvalues))
                if commit:
                    self.cnctn.commit()

                succed=True

        if succed == False:
            print("failed to add")
        return succed

    
    #updates a record in the database. figure out the sql yourself
    def updRecord(self, tableName:str, newvalue:str, sqlcond:str):
        #I do not think you can regex for a valid sql statement lmao
        succed:bool = False

        for table in TABLE_GEN:
            if tableName == table[TNAME_INDEX]:
                self.crsr.execute(gener_UPDATE.format(table=tableName,changed=newvalue,conditions=sqlcond)) 
                self.cnctn.commit()

                succed = True

        if succed == False:
            print("failed to updae")            

    def dltRecord(self, tableName:str, sqlcond:str):
        #same as previous, no way I can check for valid sql
        succed:bool = False

        for table in TABLE_GEN:
            if tableName == table[TNAME_INDEX]:
                self.crsr.execute(gener_DELETE.format(table=tableName,conditions=sqlcond)) 
                #I should probably do some error checking but I can't be bothered ngl
                self.cnctn.commit()

                succed = True

        if succed == False:
            print("failed to dlete")

    def rdRecords(self, tableName:str, valsToSee:str, sqlcond:str) ->list: #fetchall returns a string right?
        succed:bool = False
        for table in TABLE_GEN:
            if tableName == table[TNAME_INDEX]:
                self.crsr.execute(gener_SELECT.format(csvalues=valsToSee,table=tableName,conditions=sqlcond))
                retval = self.crsr.fetchall()
                succed = True
                return retval
        if succed == False:
            print("failed to read")
            return None #this is basically NULL right? should be fine
    
    def raw(self, query:str):
        self.crsr.execute(query)
        #selects describe their columns, writes don't. so: hand back rows if there are any
        retval = self.crsr.fetchall() if self.crsr.description else None
        self.cnctn.commit()
        return retval


#turns a python value into a quoted sql value, or NULL if there's nothing there.
#doubles any embedded quotes because that's how sql escapes them ('it's' -> 'it''s')
#(without this, any nickname with an apostrophe silently fails the regex and gets dropped. rip)
def sqlstr(value)->str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"

#you know, I probably could have designed this better so I didn't need all this, but whatever
def easy_user_str(userid:str, user_name:str, user_dispname:str)->str:
    return f"({sqlstr(userid)},{sqlstr(user_name)},{sqlstr(user_dispname)})"
def easy_nickn_str(userid:str, nickname:str)->str:
    #datetime('now') stays unquoted so sqlite evaluates it itself at insert time (utc).
    #don't quote it or you'll just store the words "datetime('now')" like a goober
    return f"(NULL,{sqlstr(userid)},{sqlstr(nickname)},datetime('now'))"
def easy_expln_str(nicknid:str,explanation:str)->str:
    return f"(NULL,{nicknid},{sqlstr(explanation)})"


#TESTING: (it works)
if __name__ == '__main__':
    namay = dbthingy(DB_FILEN)
    namay.crsr.execute("DROP TABLE IF EXISTS Explanations")
    namay.crsr.execute("DROP TABLE IF EXISTS Nicknames")
    namay.crsr.execute("DROP TABLE IF EXISTS Users;")


    namay.SetupDB()
    print("what the hel")
    namay.addRecord("Users",easy_user_str('23242','sebse','CERF'))
    namay.addRecord("Nicknames",easy_nickn_str('23242','henlo'))
    namay.addRecord("Users",easy_user_str('3323','slfd','sad'))
    namay.addRecord("Nicknames",easy_nickn_str('3323','sfsfgsf'))



    #namay.addRecord("Users","('234234','serIs','seris119')")
    #namay.addRecord("Nicknames","(512,'44433','faunll')")
    #namay.dltRecord("Users","user_id LIKE '%234234%'")

    '''
    namay.updRecord("Users","username='Nimt'","user_id LIKE '%234234%'")

    namay.addRecord("Users","('38273','anden2','reusm')")
    namay.addRecord("Users","('777773232','silviI','lsfisd')")
    namay.addRecord("Explanations","(22643,512,'underwent a transformaiton')")

    sn = namay.rdRecords("Users","*","")
    print(sn)

    namay.dltRecord("Users","user_id LIKE '%777773232%'")

    sn = namay.rdRecords("Users","*","")
    print(sn)
    '''
