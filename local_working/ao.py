from telegram.ext import *
from telegram import *
from uuid import uuid4
import random
import time
import logging
import threading
import math
from utils import *
from name import *
import os
import sys
ready = False
LIMIT_PLAYERZ = 100
NUM_BOT = 0
ROUND = 0
MAX_LOOT = 21
BONUS_STAY = MAX_LOOT/2 + 2
MATRIX_DIM = 9
all_ids_list = [] #notify all playetrs that the game has finished
p = os.path.join(sys.path[0], "TOKEN.txt")
f = open(p, "r")
TOKEN = str(f.readline()).strip()
u = Updater(token=TOKEN, use_context=True)



def start(update, context):
    global all_ids_list
    name = update.message.from_user.username
    if len(context.bot_data) == LIMIT_PLAYERZ:
        update.message.reply_text("sorry, the lobby is full. Wait until it will be finished.")
        if(update.effective_chat.id not in all_ids_list): all_ids_list.append(update.effective_chat.id)
        return
    if not ready:
        key = generate_key(random.randint(1,101))
        context.bot.send_message(chat_id=update.effective_chat.id, text="Hi, and welcome to Telegram Battle Royal", reply_markup=telegram.ReplyKeyboardRemove())
        user_id = update.effective_chat.id
        print("player", name , " id: ",user_id, "joined"," he is the n° ", len(context.bot_data))
        all_ids_list.append(user_id) 
            #l'utente ha gia partecipato
        if user_id in context.bot_data.keys():
            update.message.reply_text("you can not play two times :(")
            print("you can not play two times :(\n")
            
        else :     #l'utente non ha ancora partecipato
            context.bot_data[user_id] = {"loot": key, "pos": None, "bonus": None, "bot":False, "name": name, "round" : -1, "push": 0} #Struttura dati che tiene conto dei giocatori del loot e della posizione

            update.message.reply_text("You joined!\nIf you don't know how to play, simply write 'help' ")
            print("1context.bot_data = ",context.bot_data,"\n") 
            
            if len(context.bot_data) == 1:     #se è il primo giocatore parte il timer per il matchmaking
                seconds = 30
                update.message.reply_text("you are the first one, so now wait "+ str(seconds)+ " seconds for other players")
                u.job_queue.run_repeating(callback_waiting, interval=10, first=0, name ="diocane")
            #attesa fino a che sta nza piena o non finisce il tempo
            
    else:
        update.message.reply_text("a match has already started. wait until it will be finished.")
        if(update.effective_chat.id not in all_ids_list): all_ids_list.append(update.effective_chat.id)

bot_list = list()
push = -1
def callback_waiting(context: telegram.ext.CallbackContext):
    global ready
    if ready: 
        context.job.enabled = False
        context.job.schedule_removal()
        u.dispatcher.remove_handler(ch) #ch è command start 
        u.dispatcher.remove_handler(mh) #mh è string regex start

        initialization(context,len(context.bot_data))#creazione mappa
        return
    else:
        for id in list(context.bot_data.keys()):
            global bot_list,push
            ready = full(context,bot_list,push)
            if not is_a_bot(context,id):
                push+=1 #finchè non è ready push aumenta e arrivato a na certa crea i bot e fa partire la partita
                if ready: 
                    context.bot.send_message(chat_id = id, text="Ok, every one is ready, generating the map..")
                else:
                    context.bot.send_message(chat_id = id, text='Finding other players..')
                


field = None
def initialization(context, players):
    global field
    global MATRIX_DIM
    field = Field(MATRIX_DIM) 
    field.print_loot_matrix()
    a = "Map generated!\nNow choose where to drop! "

    if(len(bot_list) > 1): print("botlist: " , bot_list)

    keyboard = field.make_keyboard(MATRIX_DIM)
    reply_markup = ReplyKeyboardMarkup(keyboard,one_time_keyboard=True,resize_keyboard=True)
    for id in context.bot_data.keys():
        if not is_a_bot(context,id):
            context.bot.send_message(chat_id = id, text=a, reply_markup=reply_markup)
    activate_drop_handlers()
    
    for players in bot_list:
        i = random.randint(0,field.w-1)
        j = random.randint(0,field.h-1)
        context.bot_data[players]["pos"] = str(i)+','+str(j)
        context.bot_data[players]["loot"] += field.get(int(i),int(j))

once = True
def drop_player(update, context):
    global once
    global ROUND
    if context.bot_data[update.effective_chat.id]["pos"] == None:
        s = "Ok, you will be dropped in "
    else:
        s = "You moved in "
        once = True
    drop_coordinates = update.message.text
    if(drop_coordinates[0] == "☠"): drop_coordinates = drop_coordinates[1:]
    print(s,drop_coordinates)
    update.message.reply_text(s+drop_coordinates)
    
    context.bot_data[update.effective_chat.id]["pos"] = drop_coordinates #aggiunge il dato sulla posizione 
    context.bot_data[update.effective_chat.id]["round"] = ROUND #aggiunge il dato sulla round

    i,j = drop_coordinates.split(",")
    loot = field.get(int(i),int(j))

    talk_about(loot,update,context) #che tipo di loot ha trovato
    context.bot_data[update.effective_chat.id]["loot"]+=loot
    print(context.bot_data)

    if (once) : u.job_queue.run_repeating(callback_wait_other_players, interval=10, first=2, name ="diocane")
    once = False

def activate_drop_handlers():
    global dp
    u.dispatcher.add_handler(dp)   #dp = MessageHandler(DropFilter(), drop_player)

regularize_sending_message = 0
def callback_wait_other_players(context: telegram.ext.CallbackContext):
    global ROUND,field,regularize_sending_message
    to_drop = " to drop"
    if(ROUND > 1): to_drop = ""
    ok = True
    for players in context.bot_data.keys(): #assegno al player la posizione se non ce l ha gia
        if not is_a_bot(context,players):
            if(context.bot_data[players]["round"] < ROUND or context.bot_data[players]["pos"] == None): #il player non ha ancora scelto la pos
                ok = False
                regularize_sending_message+=1
                return
            if(context.bot_data[players]["round"] == ROUND):
                if(regularize_sending_message % 5 == 0):
                    context.bot.send_message(chat_id = players, text="wait other players"+ to_drop)
    if (ok and len(context.bot_data) > 0) :
        context.job.enabled = False
        context.job.schedule_removal()
        if(ROUND != 0):
            for bot in bot_list:
                if (bot in context.bot_data):
                    if( context.bot_data[bot]["loot"] < -4 or context.bot_data[bot]["directions"] == []): 
                        del context.bot_data[bot]
                        bot_list.remove(bot)
                    else:
                        pos = context.bot_data[bot]["pos"]
                        i,j = pos.split(",")
                        i = int(i)
                        j = int(j)
                        context.bot_data[bot]["loot"] += field.get(int(i),int(j))
        ROUND+=1 
        #print(context.bot_data)       
        start_fight(context) #called only once!!!
        return

def start_fight(context): #called only once!!!
    enemies_lists = list()
    killed_lists = list()
    ok = True
    for host in context.bot_data.keys():
        for enemies in enemies_lists:
            if host in enemies.keys():  
                ok = False
        if(ok):
            i,j = context.bot_data[host]["pos"].split(",")
            if(i[0] == "☠"): i = i[1]
            i = int(i)
            j = int(j)
            enemies_of_host = get_enemies(context.bot_data,host,i,j) #{nome_enemy:loot,....}
            enemies_lists.append(enemies_of_host)
            print("host: ", host, "enemies_of_host: ", enemies_of_host)
            killed_players = fight(host,enemies_of_host,context)
            if(len(killed_players)>0):killed_lists += killed_players
            print("killed_lists: ", killed_lists)
            ok = True
        if( context.bot_data[host]["loot"] < -2): #DIED FOR TOXIC
            died_due_toxic = "oh, no, you died due to the toxic gas! 😯\n Next time try to stay inside the safezone!"
            if not is_a_bot(context, host): context.bot.send_message(chat_id = host, text=died_due_toxic, reply_markup=telegram.ReplyKeyboardRemove())

    for killed in killed_lists:
        del context.bot_data[killed]

    next_round(context)

#---------menu callbacks
def stay_confirm(update,context): #utente conferma di volersi fermare e aggiorna il round
    global ROUND, BONUS_STAY
    context.bot_data[update.message.chat_id]["bonus"] =  BONUS_STAY
    pos = context.bot_data[update.message.chat_id]["pos"]
    context.bot_data[update.message.chat_id]["round"] = ROUND
    update.message.reply_text("ok, you decided to stay here, in "+ str(pos)+ " gaining a bonus of " + str(BONUS_STAY))
    u.job_queue.run_repeating(callback_wait_other_players, interval=10, first=2, name ="diocane")
#---------menu callbacks
toxic_perimeter = 0
def next_round(context):
    print(context.bot_data)
    global ROUND
    global field
    global toxic_perimeter
    global MATRIX_DIM
    u.dispatcher.add_handler(MessageHandler(Filters.text("stay here"),stay_confirm))

    s = "you survived to the drop. But it's only the start,"
    left = "\nOPPONENTS LEFT: " + str(len(context.bot_data)-1 )
    toxic_string = ""
    if(ROUND > 1):  s = ""
    
    #utente rimasto solo vince
    if ( len(context.bot_data) == 1 and not is_a_bot(context,next(iter(context.bot_data)))):
        win_string = "🎉 VICTORY!! 🎉 YOU ARE THE ONLY SURVIVE 🎆"
        context.bot.send_message(chat_id = next(iter(context.bot_data)), text=win_string)
        restart(context)
        
    else:
        at_least_one_p = False
        if(ROUND % 2 == 0 and ROUND > 1): #parte la safe
            field.reduce_safe_zone(toxic_perimeter)
            toxic_perimeter+=1
            toxic_string = "\n\n🚨NOW BE CAREFUL🚨 because the toxic area is coming and will subtract you points!, the places with the toxic area are signed with ☠" 
        for player in context.bot_data.keys():
            if not is_a_bot(context,player):
                at_least_one_p = True
                pos = context.bot_data[player]["pos"]

                #creazione keyboard
                keyboard = make_moving_keyboard(pos,MATRIX_DIM,field) 
                next_step_keyboard = ReplyKeyboardMarkup(keyboard,one_time_keyboard=True,resize_keyboard=True)

                total = "Ok, "+s+"\nNEXT ROUND! " + left + "\nChoose your next move: \n-Move to another adjacent position\n-Stay here, gaining a bonus"
                if( ROUND > 4 and random.randint(0,1) == 1): #aiuta dando informazioni sul centro
                    center_tip_string = center_tip(field,pos)
                    total+= center_tip_string
                context.bot.send_message(chat_id = player, reply_markup=next_step_keyboard, text=total+toxic_string) 
            else: #BOT MOVEMENT
                AI_level = 1
                if(not at_least_one_p):
                    restart(context)
                    break
                else:
                    bot_movement(context,player,AI_level,field) 
                
                
                
    
            
def bot_movement(context,player,AI_Level,field):
    bot = player
    global MATRIX_DIM,ROUND
    context.bot_data[bot]["round"] = ROUND
    pos = context.bot_data[bot]["pos"]
    i,j = pos.split(",")
    i = int(i)
    j = int(j)
    directions = []
    if(AI_Level == 0):
        if(i-1 >= 0): 
            directions.append(str(i-1) + "," + str(j))
            if(j-1 >= 0): 
                directions.append(str(i-1) + "," +str(j-1))
            if(j+1 < MATRIX_DIM) : 
                directions.append(str(i-1) + "," +str(j+1))       
        if(i+1 < MATRIX_DIM): 
            directions.append(str(i+1) + "," + str(j))
            if(j-1 >= 0): 
                directions.append(str(i+1) + "," +str(j-1))
            if(j+1 < MATRIX_DIM) : 
                directions.append(str(i+1) + "," +str(j+1))   
        if(j-1 >= 0): 
            directions.append(str(i) + "," +str(j-1))   
        if(j+1 < MATRIX_DIM) : 
                directions.append(str(i) + "," +str(j+1))   
    else:
        if(i-1 >= 0): 
            if(field.field_matrix[i-1][j]>0):
                directions.append(str(i-1) + "," + str(j))
            if(j-1 >= 0): 
                if(field.field_matrix[i-1][j-1]>0):
                    directions.append(str(i-1) + "," +str(j-1))
            if(j+1 < MATRIX_DIM) : 
                if(field.field_matrix[i-1][j+1]>0):
                    directions.append(str(i-1) + "," +str(j+1))       
        if(i+1 < MATRIX_DIM): 
            if(field.field_matrix[i+1][j]>0):
                directions.append(str(i+1) + "," + str(j))
            if(j-1 >= 0): 
                if(field.field_matrix[i+1][j-1]>0):
                    directions.append(str(i+1) + "," +str(j-1))
            if(j+1 < MATRIX_DIM) : 
                if(field.field_matrix[i+1][j+1]>0):
                    directions.append(str(i+1) + "," +str(j+1))   
        if(j-1 >= 0): 
            if(field.field_matrix[i][j-1]>0):
                directions.append(str(i) + "," +str(j-1))   
        if(j+1 < MATRIX_DIM) : 
            if(field.field_matrix[i][j+1]>0):
                directions.append(str(i) + "," +str(j+1))   
    num_directions = len(directions)-1
    if (num_directions >= 0):
        pos = directions[random.randint(0,num_directions)] #una direzione disponibile a caso
    else:
        pos = str(i) + "," +str(j)
    print("directions of bot: " , bot , "\n",directions)
    context.bot_data[bot]["directions"] = directions



ch = CommandHandler('start', start)
mh = MessageHandler(Filters.regex('^(S|s)(T|t)(a|A)(R|r)(T|t)'), start)
dp = MessageHandler(DropFilter(), drop_player)

def restart(context):
    global ROUND,ready,bot_list,push,field,once,toxic_perimeter,all_ids_list,regularize_sending_message
    regularize_sending_message = 0
    ROUND = 0
    ready = False
    bot_list.clear()
    push = -1
    # field = None
    once = True
    toxic_perimeter = 0

    ch = CommandHandler('start', start)
    mh = MessageHandler(Filters.regex('^(S|s)(T|t)(a|A)(R|r)(T|t)'), start)
    u.dispatcher.add_handler(ch)  #ch è command start #mh è string regex star
    u.dispatcher.add_handler(mh)

    u.dispatcher.remove_handler(dp) #dp = MessageHandler(DropFilter(), drop_player)


    for ids in all_ids_list:
        context.bot.send_message(chat_id = ids, text="A GAME HAS BEEN FINISHED. Type start to play! ") 
    all_ids_list.clear()
    context.bot_data.clear()


u.start_polling()

def main():
    #Struttura dati che tiene conto dei giocatori del loot e della posizione
    # context.bot_data[user_id] = {"loot": key, "pos": None, "bonus": None, "bot":False, "name": name, "round" : -1} #Struttura dati che tiene conto dei giocatori del loot e della posizione
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    
    

    u.dispatcher.add_handler(ch)
    u.dispatcher.add_handler(mh)

    u.dispatcher.add_handler(CommandHandler('stop', stop_playing))
    u.dispatcher.add_handler(MessageHandler(Filters.text('stop'), stop_playing))

if __name__ == '__main__':
    main()
