#yeah just ignore this lol

'''

#okay imma be real I just followed along a tutorial for half of this crap
#don't get me started on APIs
import discord
#from discord.ext import commands #okay so the one guy had this but I think I don't actually need it? just overcomplicates things
from discord import app_commands
import constants
import db


#ok lets be done for the day
#things you were working on:
# scrape sender of every message (performance problem)
# if empty, scrape every mamber of the server
# add nickname (needs to make suer the user exists first)

class botman(discord.Client):
    autoparsing:bool
    titleshouting:bool

    datab:db.dbthingy


    def firstRun_setup(self):
        #sets up database
        self.datab = db.dbthingy(db.DB_FILENAM)
        self.datab.SetupDB()
        

        #adds all server members to database
        #might? take a while?
        for member in self.get_guild(constants.GUILD_TOKEN).members:
            self.datab.addRecord("Users",db.easy_user_str(member.id,member.name,member.global_name)) 


    async def on_ready(self):
        self.autoparsing= constants.AUTOPARSE_DEFAULT
        self.titleshouting=constants.TITLESHOUT_DEFAULT
        self.datab = db.dbthingy(db.DB_FILENAM)

        #you have to like sync it otherwise teting gets annoying cus it takes too long
        #but this limits it to 1 server? ah well whatever
        await tree.sync(guild=discord.Object(id=constants.GUILD_TOKEN))
        print("longged on")
    
    async def on_message(self, message:discord.Message):
        if(message.author !=self.user):
           
            await message.channel.send("bonjor")
        
            if(message.mentions):
                for x in message.mentions:
                    await message.channel.send(f"in here: {x.nick}, actual name: {x.global_name}, TRUE name {x.name}")
            else:
                await message.channel.send("noone mentoind")

    async def on_member_update(self, before:discord.Member, after:discord.Member):
        if not self.autoparsing:
            return
        else:
            if after.nick != before.nick:
                self.datab.addRecord("Nicknames",db.easy_nickn_str(after.id,after.nick))
                print("nickname change detected, added to db")

        
    


intents = discord.Intents.default()
intents.message_content = True
intents.members=True

client = botman(intents=intents)
tree = app_commands.CommandTree(client)

#ok yeah I don't really get this lol
#apparently the @ means its a parasite to another function?
#(still seems weird that we're defining a function in the middle of running code but that's python for you I guess)
@tree.command(name="testmee",description="pelaseworks",guild=discord.Object(id=constants.GUILD_TOKEN))
@app_commands.checks.has_role("SPECIALLL")
async def testcmdd(interac:discord.Interaction, id:discord.Member):
    author:discord.Member = interac.user
    wusa:int = author.id

    role = discord.utils.get(interac.guild.roles, name="SPECIALLL")
    await interac.response.send_message(f" {role.mention} mentioned: {id}, {wusa}")
   # await message.channel.send("bonjour")
    #await self.response.send_message(f"made by: {arguss.author}")

@tree.command(name="add_nickname",description="register a nickname for someone",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slash_addnickn(interac:discord.Interaction, user:discord.Member, nickname:str):
    tree.client.datab.addRecord("Nicknames",db.easy_nickn_str(user.id,nickname))
  #  tree.client.datab.addRecord()

@tree.command(name="add_explanation",description="add an explanation for a nickname",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slash_addexpl(interac:discord.Interaction,nickname:str,explanation:str):
    print("helo")

@tree.command(name="getall",description="getaldf",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashgetall(interac:discord.Interaction):
    tree.client.firstRun_setup()
    await interac.response.send_message("did it?")
    
@tree.command(name="set_nickn_parse",description="decides whether bot automatically detects nickname changes or not",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slash_autopbool(interac:discord.Interaction,autoparse:bool):
    tree.client.autoparsing=autoparse
    await interac.response.send_message(f"behavior set to: {tree.client.autoparsing}")

@tree.command(name="set_title_shouting",description="decides whether the bot will shout out someone's titles when they're mentioned",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slash_replies(interac:discord.Interaction,titleyell:bool):
    tree.client.titleshouting=titleyell
    await interac.response.send_message(f"behavior set to {tree.client.titleshouting}")

#dump entire table
@tree.command(name="dump_table", description="spits out raw sql file",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashdumptable(interac:discord.Interaction):
    table = discord.File("nicknames.db",filename="nicknames.db")
    await interac.response.send_message("file",file=table,ephemeral=True)
#}


#grab nicknames (and ids) of a user
@tree.command(name="print_nicknames",description="prints all of a user's nicknames",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashgetnicks(interac:discord.Interaction, user:discord.Member, private:bool):
    result =tree.client.datab.rdRecords("Nicknames","nickn_id,nickname",f"WHERE user_id = {user.id}")
    print(user.id)
    print(result)
    await interac.response.send_message(result,ephemeral=private)


#grab a nickname, and its explanation
@tree.command(name="explain_nickname",description="explains a nickname",guild=discord.Object(id=constants.GUILD_TOKEN))
async def slashexplnnick(interac:discord.Interaction, nicknid:int, private:bool):
    #a sensible person would have just done a join but my design is too fragile for that
    result =tree.client.datab.rdRecords("Nicknames","nickname",f"WHERE nickn_id = {nicknid}")
    result +=tree.client.datab.rdRecords("Explanations","explanation",f"WHERE nickn_id = {nicknid}")
    await interac.response.send_message(result,ephemeral=private)


client.run(constants.BOT_TOKEN)

# features:
# \setmode (auto/manual)
#       -auto parses for nicknames, needs command authorization
#       \setnickname (user, nickname)
#       \removenick (user, nickname)
# \togglemessaging (on/off)
#       -whether it shouts messages or not
# \setcooldown(time_sec)
#       -cooldown for the same person's nickname
# \pulldb()
#       -pulls db file

#automatically? fills users table
#automatically detect changes in usersname
    #-if not in users addto users
#slash command to add to 'expln' table
#slash command to read out explanation(s)
#update and or delete are too much effort
#slash command to just download the db
'''