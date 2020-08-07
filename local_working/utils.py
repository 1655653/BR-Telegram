import time
import telegram.ext
import math
from telegram.ext import *
import logging
from uuid import uuid4
from telegram.ext import Updater, CommandHandler
import time
import random
import re
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup,ReplyKeyboardMarkup
from name import *

MAX_LOOT = 21 #send info about the quality of loot
DEBUG_PLAYERZ = 5
class Field:

    def __init__(self, players):
        self.players = players
        #build the loot matrices
        self.w,self.h = players,players
        self.field_matrix =  [[random.randint(1,MAX_LOOT) for x in range(self.w)] for y in range(self.h)]
        self.center = str(random.randint(1,players-1))+","+str(random.randint(1,players-1))

    def print_loot_matrix(self):
        print('\n'.join([''.join(['{:4}'.format(item) for item in row]) for row in self.field_matrix]))
    
    def get(self,i,j):
        return self.field_matrix[i][j]
    def sett(self,i,j,value):
        self.field_matrix[i][j] = value
    
    def make_keyboard(self,n):
        L = []
        for i in range(n):
            LL = []
            for j in range(n):
                LL.append(str(i)+","+str(j))
            L.append(LL)
        return L
        # return [[L.append([str(i)+","+str(j) for j in range(n)])]for i in range(n)]
    
    def reduce_safe_zone(self,n):
        center_i,center_j = self.center.split(",")
        center_i = int(center_i)
        center_j = int(center_j)
        if (n < 5):  #cornici
            for v in range(n,self.players-n):
                if(center_i != 0+n and center_j != v):
                    self.field_matrix[0+n][v] = -4*(n+1) #up

            for v in range(n,self.players-n):
                if(center_i != self.players-1-n and center_j != v):
                    self.field_matrix[self.players-1-n][v] = -4*(n+1)#down
            
            for v in range(n,self.players-n):
                if(center_j != 0+n  and center_i != v):
                    self.field_matrix[v][0+n] = -4*(n+1) #left      
            for v in range(n,self.players-n):
                if(center_j != self.players-1-n and center_i != v):
                    self.field_matrix[v][self.players-1-n] = -4*(n+1) #right
        else: #elimina una casella alla volta fino ad arrivare al centro
            for v in range(self.players):
                for m in range(self.players):
                    if( (v == center_i and m != center_j)   or (v != center_i and m == center_j)):
                        if( self.field_matrix[v][m] > 0 ):
                            self.field_matrix[v][m] = -4*(n-1)
                            break
        print("-----------MAP REDUCED--> round ", n, "center: ", self.center, "value: ", self.field_matrix[center_i][center_j])
        self.print_loot_matrix()   
             

class Bot_Player:

    def __init__(self, id):
        self.id = math.ceil(id)*162

#custom filter
class DropFilter(BaseFilter):
    def filter(self, message):
        txt = message.text
        if re.search("[0-9]", txt) == None: return False
        return True

        


def is_a_bot(context,id):
    return context.bot_data[id]["bot"]

#decides when start the game and the limit of the players, Moreover CREATES THE BOTs
def full(context,bot_list,push):
    time_threshold = 3
    #BOT_GENERATION
    if(push == time_threshold): 
        NUM_BOT = random.randint(1,70)
        name_list = bot_name_generator(NUM_BOT)
        for i in range(NUM_BOT):
            bot = Bot_Player(random.randint(1,101))
            context.bot_data[bot.id] =  {"bot": True, "loot": random.randint(0,4), "pos": None, "bonus": None, "name": name_list[i], "round" : -1, "directions": []}
            bot_list.append(bot.id)
    
    if(push > time_threshold): 
        print("PUSH = ", push)
        return True
    global DEBUG_PLAYERZ
    if(len(context.bot_data) - len(bot_list) >= DEBUG_PLAYERZ): 
        print("DEBUG PLAYEEEERZ")
        return True # adesso controlla che ci siano 2 giocatori
                                            #teoricamente parte quando scade un timer o se si è raggiunto il limite
    return False

def generate_key(n):
    r = str(uuid4()).split("-")[0]
    k = n
    for i in r:
        k+= ord(i)
    return k/100 #da 4 a 8

def talk_about(loot,update,context):
    t = "you found a "
    def about(MAX_LOOT):
        if(loot == MAX_LOOT): return ("NO-PLUS-ULTRA",1)
        if(loot >= MAX_LOOT*(4/5)): return ('LEGEN.. wait for it.. DARY',0)
        if(loot >= MAX_LOOT*(3/5)): return ('EPIC',0)
        if(loot >= MAX_LOOT*(2/5)): return ('RARE',0)
        if(loot >= MAX_LOOT*(1/5)): return ('NON COMMON',0)
        return ('COMMON',0)
    dd =  "   "+str(loot) + "\n...waiting for other players..."
    description, n= about(MAX_LOOT)
    d = " "
    if (n==1): d = ". This is the best weapon in the game. It's you lucky day!" 
    update.message.reply_text(t + description+" weapon" + d + dd)


def get_enemies(data_structure,id,i,j):
    L = {}
    for nick in data_structure.keys():
        if nick != id:
            Pi,Pj = data_structure[nick]["pos"].split(",")
            Pi = int(Pi)
            Pj = int(Pj)
            if (Pi == i and Pj == j):
                L[nick]=data_structure[nick]["loot"]
    return L


#fight of the host vs all enemies. if he dies the winner is the host
def fight(host,enemies_of_host,context):
    killed = list()
    for enemy in enemies_of_host:
        #points assigment
        host_points = context.bot_data[host]["loot"]
        if (context.bot_data[host]["bonus"]) != None: host_points+= context.bot_data[host]["bonus"]
        host_points+= random.randint(1,7)

        enemy_points = context.bot_data[enemy]["loot"]
        if (context.bot_data[enemy]["bonus"]) != None: enemy_points+= context.bot_data[enemy]["bonus"]
        enemy_points+= random.randint(1,7)

        if(enemy_points == host_points) : host_points = enemy_points+random.choice([-1,1])
        
        #string management
        win = "⚔ WooooW! ⚔ you won the fight against player: "
        lost1 = "😧 OH NO! 😧Your opponent, player "
        name_enemy = str(enemy)
        if( context.bot_data[enemy]["name"] != None): name_enemy = str(context.bot_data[enemy]["name"]) 
        name_host = str(host)
        if( context.bot_data[host]["name"] != None): name_host = str(context.bot_data[host]["name"])
        lost3 = ",💀defeated you!💀  see you next game 👋 ! F"
        rob = "\n you robbed from him "
        rob2 = " points! 💰💰"
        #il vincitore aggiorna il suo punteggio di enemy_points/4
        if(host_points > enemy_points) : 
            context.bot_data[host]["loot"]+=math.ceil(enemy_points/4)

            rob = rob + str(enemy_points/4) + rob2
            if not is_a_bot(context, host): context.bot.send_message(chat_id = host, text=win +  name_enemy + rob , reply_markup=telegram.ReplyKeyboardRemove())

            if not is_a_bot(context, enemy): context.bot.send_message(chat_id = enemy, text=lost1 + name_host +lost3, reply_markup=telegram.ReplyKeyboardRemove())
            killed.append(enemy)

            
        elif(host_points < enemy_points) : 
            context.bot_data[enemy]["loot"]+=math.ceil(enemy_points/4)

            rob = rob + str(host_points/4) + rob2

            if not is_a_bot(context, enemy): context.bot.send_message(chat_id = enemy, text=win+  name_host + rob, reply_markup=telegram.ReplyKeyboardRemove())
            if not is_a_bot(context, host): context.bot.send_message(chat_id = host, text= lost1+ name_enemy +lost3, reply_markup=telegram.ReplyKeyboardRemove())
            killed.append( host)
            host = enemy
    return killed





def stop_playing(update, context):
    update.message.reply_text("you decided to stop playing. see you space cowboy..")
    user_id = update.effective_chat.id
    if user_id in context.bot_data.keys():
        del context.bot_data[user_id]







def make_moving_keyboard(pos,nplayers,field): #vedi, se l'utente sta fuori la mappa do stringa s, se c'è la toxic metti teschio altrimenti i,j
    i,j = pos.split(",")
    i = int(i)
    j = int(j)
    s = "can't go here ❌"
    b = "stay here"
    if(field.field_matrix[i][j]<0):b = "☠" + b + "☠" 
    keyboard = [[s,s,s],[s,b,s],[s,s,s]]

    if(i-1 >= 0): 
        if(field.field_matrix[i-1][j]>0):
            keyboard[0][1] = str(i-1) + "," + str(j)
        else:
            keyboard[0][1] = "☠"+str(i-1) + "," + str(j)
        if(j-1 >= 0): 
            if(field.field_matrix[i-1][j-1]>0):
                keyboard[0][0] = str(i-1) + "," +str(j-1)
            else:
                keyboard[0][0] = "☠"+str(i-1) + "," + str(j-1)
        
        if(j+1 < nplayers) :
            if(field.field_matrix[i-1][j+1]>0):
                keyboard[0][2] = str(i-1) + "," +str(j+1)
            else:
                keyboard[0][2] = "☠"+str(i-1) + "," + str(j+1)

    if(i+1 < nplayers): 
        if(field.field_matrix[i+1][j]>0):
            keyboard[2][1] = str(i+1) + "," + str(j)
        else:
            keyboard[2][1] = "☠"+str(i+1) + "," + str(j)
        
        if(j-1 >= 0): 
            if(field.field_matrix[i+1][j-1]>0):
                keyboard[2][0] = str(i+1) + "," +str(j-1)
            else:
                keyboard[2][0] = "☠"+str(i+1) + "," +str(j-1)
        
        if(j+1 < nplayers):
            if(field.field_matrix[i+1][j+1]>0):
                keyboard[2][2] = str(i+1) + "," +str(j+1)
            else:
                keyboard[2][2] = "☠"+str(i+1) + "," +str(j+1)
    
    if(j-1 >= 0): 
        if(field.field_matrix[i][j-1]>0):
            keyboard[1][0] = str(i) + "," +str(j-1)
        else:
            keyboard[1][0] ="☠"+ str(i) + "," +str(j-1)
    
    if(j+1 < nplayers):
        if(field.field_matrix[i][j+1]>0):
            keyboard[1][2] = str(i) + "," +str(j+1)
        else:
            keyboard[1][2] ="☠"+ str(i) + "," +str(j+1)
    
    return keyboard



def center_tip(field,player_pos):
    s1 = "\n📰📰AN USEFUL INFO ABOUT THE CENTER HAS BEEN LEAKED : IT'S "
    s2 = "WITH RESPECT TO YOUR POSITION"
    c = field.center
    centeri,centerj = c.split(",")
    centeri = int(centeri)
    centerj = int(centerj)

    player_posi,player_posj = player_pos.split(",")
    player_posi = int (player_posi)
    player_posj = int (player_posj)
    coo_1 = ""
    coo_2 = ""
    if (centeri > player_posi):
        coo_1 = " SOUTH "
    if (centeri == player_posi):
        coo_1 = " CENTER "
    if (centeri < player_posi):
        coo_1 = " NORTH "
    if (centerj > player_posj):
        coo_2 = " EAST "
    if (centerj == player_posj):
        coo_2 = " CENTER "
    if (centerj < player_posj):
        coo_2 = " WEST "

    return s1+coo_1+coo_2+s2

