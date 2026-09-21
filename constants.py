#constants because this is apparently how you do it in python? I think?
#idk there's no #defs so...

import os

#secrets live in .env (gitignored) or actual environment variables — never in here,
#this file is committed. real env vars win over .env, .env wins over the placeholders.
#(.env is relative like DB_FILENAM below, so start the bot from the repo dir —
#start_bot.bat already does that)
def __load_env():
    try:
        with open(".env") as envfil:
            for line in envfil:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass #no .env? fine, env vars or placeholders it is
__load_env()

#bot thingies
BOT_TOKEN :str = os.environ.get("BOT_TOKEN", 'i forget where you find this')
GUILD_TOKEN  = int(os.environ.get("GUILD_TOKEN", "2")) #i forget where you find this either

ROLE = "Shadow pavilion"

#the dyno/carl-bot logging channel. the mining commands are gone, but the dump file they
#left behind (logdump_<this id>.jsonl) is still what dates and orders everyone's
#nicknames in /print_nicknames, so the id stays.
#not a secret — it's an id, worst case someone points their own bot at a channel they can't read
LOG_CHANNEL:int = int(os.environ.get("LOG_CHANNEL", "1404266860937216082"))

#change these if you want since otherwise you'll have to everytime you restart it
AUTOPARSE_DEFAULT = True 
TITLESHOUT_DEFAULT = True

TITLESHOUT_MSG: str = "{x} hte great {y} blah bla hbal"


#db thingies
    #should these be in the db file?? idk maybe
    #python doesn't really seem to have private values? or consts or anything
    #so I guess I'll just put them here
DB_FILENAM: str = 'nicknames.db'

#ok so I think I read that __x makes it semi-invisible outside this file? (though i'm still unsure if __ or _ is more proper...)
__USERS_SQLCOM:str = '''
                    CREATE TABLE IF NOT EXISTS Users(
                        user_id varchar(35) PRIMARY KEY,
                        username varchar(35),
                        display_name varchar(35)
                    );
                '''
__NICKN_SQLCOM:str ='''
                    CREATE TABLE IF NOT EXISTS Nicknames(
                        nickn_id INTEGER PRIMARY KEY,
                        user_id varchar(35),
                        nickname varchar(35),
                        FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    );
                '''
__EXPLN_SQLCOM:str = '''
                    CREATE TABLE IF NOT EXISTS Explanations(
                        expln_id INTEGER PRIMARY KEY,
                        nickn_id int,
                        explanation varchar(80),
                        FOREIGN KEY (nickn_id) REFERENCES Nicknames(nickn_id)
                    );
                '''

__USERS_TABLE_REGEX:str = r"^\(([\"\'].+[\"\']|NULL),([\"\'].+[\"\']|NULL),([\"\'].+[\"\']|NULL)\)$"    #beautiful isn't it?
__NICKN_TABLE_REGEX:str = r"^\(([0-9]+|NULL),([\"\'].+[\"\']|NULL),([\"\'].+[\"\']|NULL)\)$"            #lmao
__EXPLN_TABLE_REGEX:str = r"^\(([0-9]+|NULL),[0-9]+,([\"\'].+[\"\']|NULL)\)$"  #regexes are actually op

#anyway this all isn't strictly necessary its just my way of ensuring that if you add more tables
#you add all these other things too
#(...if this were java there'd be some nonsense about injecting a class or something stupid like that)

TABLE_GEN:list = [ ['Users', __USERS_SQLCOM, __USERS_TABLE_REGEX], ['Nicknames', __NICKN_SQLCOM, __NICKN_TABLE_REGEX], ['Explanations', __EXPLN_SQLCOM, __EXPLN_TABLE_REGEX]]
#so basically this is the guy you want to use outside of here
TNAME_INDEX:int = 0
TSQL_INDEX:int = 1
TREGEX_INDEX:int = 2
#just to avoid magic numbers idk if python people do this


