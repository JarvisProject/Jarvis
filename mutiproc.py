from multiprocessing import Process, Pipe
from subprocess import Popen, PIPE
import subprocess
import threading
import sys
import time
import speech
import cPickle

class ConditionValue:
    def __init__(self, n):
        self.val = n
        self.cv = threading.Condition()
        
    def wait_for(self,n,wait_time=None):
        self.cv.acquire()
        while self.val != n:
            self.cv.wait(wait_time)

    def release():
        self.cv.release()
        
    def set_release(self,n):
        self.val = n
        self.cv.notifyAll()
        self.cv.release()

    def get(self):
        return self.val

cval = ConditionValue(0)
speech_parent, speech_child = Pipe()

### Voice input        
def speech_callback(phrase, listener):
    #prints what I said
    speech_child.send(": %s\n" %(phrase))
##    sys.stdout.flush()

    if phrase == "turn off speech" or phrase == "Turn off speech" or \
       phrase == "turnoff speech" or phrase == "Turnoff speech":
        #if I say "turn off speech"
        #Jarvis says "yes sir"
        speech.say("Speech uninitialized sir.")
        listener.stoplistening()
        speech_do_work(False)

    if phrase == "turn on speech" or phrase == "Turn on speech":
        #if I say "turn on speech"
        #Jarvis says "Speech initialized sir"
        speech.say("Speech initialized sir")
        listener.stoplistening()
        speech_do_work(True)   

def speech_do_work(boolean):
    if boolean:
        #if I say "turn on speech"
        #Jarvis will listen to anything I say and print it
        speech.listenforanything(speech_callback)
    else:
        #if I say "turn off speech"
        #it will wait for me to say "turn on speech"
        speech.listenfor(["turn on speech"], speech_callback)

### SMS Input    
import imaplib
import email
import time
import threading

#log in
mail =  None

#see how many unseen messages there are
def LogGmail():
    mail = imaplib.IMAP4_SSL('imap.gmail.com','993')
    mail.login('jarvisatyourservice1@gmail.com', '15963212')  

def UnsMess():
    while 1:
        LogGmail()
        mail.select()
        #searches how many unseen "['OK']['<number>']"
        aaa, bbb = mail.search(None,'UNSEEN')
        #if the number of unseen is more than 0 read it
        if bbb != ['']:
            RecMess()

def RecMess():
    #set to inbox
    LogGmail()
    mail.select('inbox')
    #read the lastest message
    #get uids of all messages
    result, data = mail.uid('search', None, 'ALL') 
    uids = data[0].split()

    result, data = mail.uid('fetch', uids[-1], '(RFC822)')
    m = email.message_from_string(data[0][1])
    if m.get_content_maintype() == 'multipart': #multipart messages only
        for part in m.walk():
            #find the attachment part
            if part.get_content_maintype() == 'multipart': continue
            if part.get('Content-Disposition') is None: continue

            #save the attachment in the program directory
            filename = part.get_filename()
            fp = open(filename, 'wb')
            fp.write(part.get_payload(decode=True))
            fp.close()
            print '%s saved!' % filename
        #somehow notify Jarvis C++ that new txtfile has been saved
        #Jarvis will read it, interpret, execute
        #then send the string to
        #sendmess(string)
    sendmess('Sir, what shall I do now')
    delete_inbox()


#delete the last email
import getpass
import re

pattern_uid = re.compile('\d+ \(UID (?P<uid>\d+)\)')
def parse_uid(data):
    match = pattern_uid.match(data)
    return match.group('uid')
def delete_inbox():
    mail.select(mailbox = 'inbox', readonly = False)
    resp, items = mail.search(None, 'All')
    email_ids  = items[0].split()
    mail.store(email_ids[-1], '+FLAGS', '\\Deleted')
    mail.expunge()
#****sending from computer****
import smtplib
server = smtplib.SMTP( "smtp.gmail.com", 587 )
server.starttls()
server.login( 'jarvisatyourservice1@gmail.com', '15963212')
def sendmess(string):
    server.sendmail( '8589976724', '8589976724@vtext.com', string )


### Jarvis engine
def CallJarvis():
    p = Popen("Jarvis_3.exe", stdin=PIPE, stdout=PIPE, shell=True) #stderr=child_conn)
    return p

### Helper launcher for inputs
def launch_proc(target, idx, name, pipe_pair=None):
    if pipe_pair is None:
        parent_conn, child_conn = Pipe()
    else:
        parent_conn, child_conn = pipe_pair
    print "Pipe: ", parent_conn,", ",child_conn
    p = threading.Thread(target=target, args=(child_conn,) )
    p.start()
    return (p, parent_conn, idx, name)  
    
#lock = threading.Lock()
cv = threading.Condition()
cv_read = threading.Condition()
cv_write = threading.Condition()

### Voice
def Voice(child_conn):
##    #Jarvis will first listen for either turn on speech or turn off speech
##    listener = speech.listenfor(["turn on speech",
##                                 "Turn on speech",
##                                 "Turn off speech",
##                                 "turn off speech",
##                                 "turnoff speech",
##                                 "Turnoff speech"], speech_callback)
    while True:
        cval.wait_for(0)
        line = speech.input()
        child_conn.send(line)
        print "Voice:",line
        cval.set_release(2)
    
### Console input
def Console(child_conn):
    while True:
        cval.wait_for(0)
        print "PROMPT> ",
        line = sys.stdin.readline()
        child_conn.send(line)
        cval.set_release(1)

if __name__ == '__main__':
    proc_list=[]

    ss = "James, Ddongo~~~"
    flag = True
    pstr = cPickle.dumps( (ss,flag) )
    print "pickled str: ", pstr


    (ss2, flag2) = cPickle.loads(pstr)
    print ss2, flag2
 
##    parent_conn, child_conn = Pipe()
##    p = threading.Thread(target=Console, args=(child_conn,) )
##    p.start()
##    proc_list.append( (p, parent_conn, "Console") )
##    
##    while True:
##        cval.wait_for(1)
##        msg = parent_conn.recv()
##        print "Terminal: ", msg,
##        cval.set_release(0)
##    p.join()
##    exit()


    # Launch Console & Voice
    proc_list.append( launch_proc(Console, 1, "Console") )
    #proc_list.append( launch_proc(Voice, 2, "Voice") )

    # Launch Jarvis executable
    pJarvis = CallJarvis()
    Jarvis_in = pJarvis.stdin
    Jarvis_out = pJarvis.stdout

##    pTerminal = CallTerminal()
##    Terminal_in = pTerminal.stdin
##    Terminal_out = pTerminal.stdout
    
    while True:
        ##(1) Print out the prompt of Jarvis
        print Jarvis_out.readline()
        for proc, parent_conn, idx, name in proc_list:
            ##Waiting for response of Tony Stark
            cval.wait_for(idx, 0.5)
            if(cval.get() != idx):
                cval.release()
                continue
            ## Yes. Response available from my lord
            msg = parent_conn.recv()
            print  name,": ", msg
            ##(2) Send it to Jarvis
            Jarvis_in.write(msg + "\n")
            ##(3) Take the acceptance response from Jarvis
            print Jarvis_out.readline()
            ##(4) Release condition variable
            cval.set_release(0)
            break
                
