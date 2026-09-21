#whatever I don't care anymore it's been to long I'm not gonna bother doing this properly
#nicknames tracker because I consider that actually important rather than the announcer which is cool admitedtly
#but I couldn't be bothered figuring out. do it yourself if you want


#okay imma be real I just followed along a tutorial for half of this crap
#don't get me started on APIs
import discord
from discord import app_commands
import constants
import db

#python is so annoying man I hate self.<> sooooo much 


#reference because it's a bit confusing:
'''
-member.name : actual discord username. unique, changeable.
-member.global_name : your regular name. not unique, changeable. what you see in dms.
-member.nick : server specific name. not unique, changeable.
'''
class botman(discord.Client): 
    #autodetect:bool
    #shouting:bool

    daba:db.dbthingy

    def firstRun_setup(self):
        #sets up database
        self.daba = db.dbthingy(db.DB_FILENAM)
        self.daba.SetupDB()
        #also the db thing is like not done properly at all
        #I don't care sqlalchemy is awful I had to use if for work its really really annoying

        #adds all server members to database
        #might? take a while?
        for member in self.get_guild(constants.GUILD_TOKEN).members:
            self.daba.addRecord("Users",db.easy_user_str(member.id,member.name,member.global_name)) 
            self.daba.addRecord("Nicknames",db.easy_nickn_str(member.id,member.nick))
        #}
    #}

    #don't even get me started on async but this is basically when the bot actually loads ready
    async def on_ready(self):
       # self.autoparsing= constants.AUTOPARSE_DEFAULT
        #self.titleshouting=constants.TITLESHOUT_DEFAULT

        self.daba = db.dbthingy(db.DB_FILENAM)

        #you have to like sync it otherwise teting gets annoying cus it takes too long
        #but this limits it to 1 server? ah well whatever
        await tree.sync(guild=discord.Object(id=constants.GUILD_TOKEN))
            #what is tree? good question I dunno.
        print("longged on")
    #}

    async def on_member_join(self,member):
        #we are, in fact, going to scan every person that joins this server
        self.daba.addRecord("Users",db.easy_user_str(member.id,member.name,member.global_name)) 
    #}

    #async def on_message(self, message:discord.Message):
        #scans every message written, sees if author has posted in < {timefraction},
        #if not yells out "hello mr authorname" or whatever

        #this is really stupid though scanning every single message is incredibly dumb
        #maybe there's a different function that lets me do it better but I don't remember finding one
    #}

    async def on_member_update(self, before:discord.Member, after:discord.Member):
        #incredibly convenient function that is literally exactly what I need
        if after.nick != before.nick:
            self.daba.addRecord("Nicknames",db.easy_nickn_str(after.id,after.nick))
            print("nickname change detected, added to db")  
        #we don't care if someone changed their profile pic or whatever  

    #}
#}

#still not sure what this all is
intents = discord.Intents.default()
intents.message_content = True
intents.members=True

client = botman(intents=intents)
tree = app_commands.CommandTree(client)


#call firstrun
@tree.command(name="firstrun_init",description="initializes everything for setup",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashgetall(interac:discord.Interaction):
    tree.client.firstRun_setup()
    await interac.response.send_message("setup complete?")
#}

#dump entire table
@tree.command(name="dump_table", description="spits out raw sql file",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashdumptable(interac:discord.Interaction):
    table = discord.File("nicknames.db",filename="nicknames.db")
    await interac.response.send_message("file",file=table,ephemeral=True)
#}

#grab nicknames (and ids) of a user
@tree.command(name="print_nicknames",description="prints all of a user's nicknames",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashgetnicks(interac:discord.Interaction, user:discord.Member, private:bool):
    result =tree.client.daba.rdRecords("Nicknames","nickn_id,nickname",f"WHERE user_id = {user.id}")
    await interac.response.send_message(result,ephemeral=private)
#}

#grab a nickname, and its explanation
@tree.command(name="explain_nickname",description="explains a nickname",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashexplnnick(interac:discord.Interaction, nicknid:int, private:bool):
    #a sensible person would have just done a join but my design is too fragile for that
    result =tree.client.daba.rdRecords("Nicknames","nickname",f"WHERE nickn_id = {nicknid}")
    result +=tree.client.daba.rdRecords("Explanations","explanation",f"WHERE nickn_id = {nicknid}")
    await interac.response.send_message(result,ephemeral=private)
#}

#add explanation using id
@tree.command(name="add_explanation",description="add an explanation for a nickname",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashaddexpl(interac:discord.Interaction, nicknid:int, explanation:str):
    tree.client.daba.addRecord("Explanations",db.easy_expln_str(nicknid,explanation))
    await interac.response.send_message(f"explanation '{explanation}' added",ephemeral=True)
#}

#update explanation using id
    #can't be bothered whatever just don't make mistakes lol

#emergency direct SQL
@tree.command(name="direct_sql",description="directly performs sql",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role(constants.ROLE)
async def slashemergsql(interac:discord.Interaction,query:str):
    tree.client.daba.raw(query)

    role = discord.utils.get(interac.guild.roles, name=constants.ROLE)
    await interac.response.send_message(f"{role.mention} raw executed. query: {query}")
#}



client.run(constants.BOT_TOKEN)

#current issues I can't be bothered to address:
'''
-ux is a bit bad
    (responses and whatever)
-error messages? never heard of that
    -if you do bad sql or something it wont damage anyhing but youll just get an erro in the command line and no response from the bot
-if you don't have the role you can still see the commands for some reason
-you can probably do sql injection but whatever
-notice when someone changes their actual username and not just their nicknames
-
'''
