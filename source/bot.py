from init import *
import requests,requests.auth,mimetypes,urllib.parse,aiofiles
loop = None
lastsend = None
class Server(Config):
    def __init__(self, room, **kwargs) -> None:
        super().__init__(room, **kwargs)
async def showpage(page,server,preview=False,update_lastid=False):
    html_body = ' #%d %s from %s\n' % (page['id'],page['title'],page['created_date'])
    if preview:
        url = server.server+'/api/documents/%d/thumb/' % page['id']
        file = '/tmp/%d.png' % page['id']
        thumb = requests.get(url=url, 
            auth=requests.auth.HTTPBasicAuth(server.user, server.password),
            allow_redirects=False)
        with open(file, 'wb') as f:
            f.write(thumb.content)
        await bot.api.send_image_message(server.room,file)
    await bot.api.send_markdown_message(server.room,html_body)
    if update_lastid:
        server.lastid = page['id']
        await save_servers()
@bot.listener.on_message_event
async def tell(room, message):
    global servers,lastsend
    server = None
    for server in servers:
        if server.room == room.room_id:
            break
    if server and server.room != room.room_id: return
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and match.prefix()\
    and match.command("listen"):
        server = Server({
            'room': room.room_id,
            'server': match.args()[1],
            'user': match.args()[2],
            'password': match.args()[3]
        })
        servers.append(server)
        loop.create_task(check_server(server))
        await save_servers()
        await bot.api.send_text_message(room.room_id, 'ok')
    elif match.command("search"):
        try:
            response = requests.get(
                url=server.server+'/api/documents/?query="%s"' % urllib.parse.quote(match.args()[0]),
                auth=requests.auth.HTTPBasicAuth(server.user, server.password),
                allow_redirects=False
            )
            res = json.loads(response.content)
            for page in res['results']:
                await showpage(page,server)
        except:
            pass
    elif match.command("show"):
        try:
            response = requests.get(
                url=server.server+'/api/documents/%s/' % match.args()[0],
                auth=requests.auth.HTTPBasicAuth(server.user, server.password),
                allow_redirects=False
            )
            page = json.loads(response.content)
            await showpage(page,server,True)
        except:
            pass
    elif match.is_not_from_this_bot():
        try:
            if server.room != room.room_id: return
            user = message.sender
            user = user[:user.find(':')]
            if user[:1] == '@':
                user = user[1:]
            server._client.run('ServerChat',user+':'+message.body)
            server._client.run('amx_say',user+':'+message.body)
            lastsend = user+':'+message.body
        except:
            pass
async def check_server(server):
    global lastsend,servers
    response = requests.get(
        url=server.server+'/api/documents/?pages=1',
        auth=requests.auth.HTTPBasicAuth(server.user, server.password),
        allow_redirects=False
    )
    if not hasattr(server,'lastid'):
        server.lastid = None
    while True:
        try:
            response = requests.get(
                url=server.server+'/api/documents/?ordering=-added',
                auth=requests.auth.HTTPBasicAuth(server.user, server.password),
                allow_redirects=False
            )
            res = json.loads(response.content)
            newpages = []
            for page in res['results']:
                if page['id'] != server.lastid:
                    newpages.append(page)
                else:
                    break
            for page in reversed(newpages):
                await showpage(page,server,True,True)
        except BaseException as e:
            if not hasattr(server,'lasterror') or server.lasterror != str(e):
                await bot.api.send_text_message(server.room,str(server.server)+': '+str(e))
                server.lasterror = str(e)
        await asyncio.sleep(60)
try:
    with open('data.json', 'r') as f:
        nservers = json.load(f)
        for server in nservers:
            servers.append(Server(server))
except BaseException as e: 
    logging.error('Failed to read config.yml:'+str(e))
@bot.listener.on_startup
async def startup(room):
    global loop,servers
    loop = asyncio.get_running_loop()
    for server in servers:
        if server.room == room:
            loop.create_task(check_server(server))
@bot.listener.on_message_event
async def bot_help(room, message):
    bot_help_message = f"""
    Help Message:
        prefix: {prefix}
        commands:
            listen:
                command: listen [server] [username] [password]
            search:
                command: search [phrase]
                description: searches for matching documents
            get:
                command: get [docid]
                description: downloads an document with docid
            help:
                command: help, ?, h
                description: display help command
                """
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and match.prefix() and (
       match.command("help") 
    or match.command("?") 
    or match.command("h")):
        await bot.api.send_text_message(room.room_id, bot_help_message)
bot.run()