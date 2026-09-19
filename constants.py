#constants because this is apparently how you do it in python? I think?
#idk there's no #defs so...

#bot thingies
BOT_TOKEN :str = 'i forget where you find this'
GUILD_TOKEN  = 2 #i forget where you find this either

ROLE = "Shadow pavilion"

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
                        user_id varchar[35] PRIMARY KEY,
                        username varchar[35],
                        display_name varchar[35]
                    );
                '''
__NICKN_SQLCOM:str ='''
                    CREATE TABLE IF NOT EXISTS Nicknames(
                        nickn_id INTEGER PRIMARY KEY,
                        user_id varchar[35],
                        nickname varchar[35],
                        FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    );
                '''
__EXPLN_SQLCOM:str = '''
                    CREATE TABLE IF NOT EXISTS Explanations(
                        expln_id INTEGER PRIMARY KEY,
                        nickn_id int,
                        explanation varchar[80],
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


