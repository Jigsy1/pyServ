# pyServer.py - An example of linking to an ircu based IRCd in Python.
#
# This script will not work unless you have a C:line[1] on an ircu based IRCd. (http://ircd.bircd.org/)
#
# Example commands (using JupeServ):
# -----------------------------------
# ?raw AA P #channel :Hello! - Makes the server itself say "Hello!" in #channel.
# ?raw AA M #channel +v ATAAx - Gives a +v to the user who has the numeric of ATAAx[2] on #channel.
# ?raw AA N FBI 1 1674548945 noreply fbi.gov +iko B]AAAB AAAAA :FBI
#
# ...will create the user FBI!noreply@fbi.gov with usermodes +iko and an ip of 127.0.0.1 (B]AAAB) as user AAAAA[3] on jupe server.
# NOTE: Creating AAAAA on top of AAAAA will[4] result in a SQUIT, so you might want to keep track of who has been created if you plan on doing this.
#
# ?raw AAAAA J #channel - Will make our newly created "FBI" user join #channel.
# ?raw AA J #channel - Will cause the server to SQUIT because servers cannot join channels. :P
# ?raw AA I FBI #channel - Will also cause the server to SQUIT because servers cannot invite users apparently.[5]
#
# Note: You need to use the nick, not the numeric in order to invite a user.
#
# Further reading:
# --------------------
# 1. [P10]:  http://ircd.bircd.org/bewarep10.txt (recommended)
# 2. [P10]:  https://web.archive.org/web/20100209040721/http://www.xs4all.nl/~carlo17/irc/P10.html
# 3. [Raws]: https://modern.ircdocs.horse/index.html
# 4. [P10]:  http://web.mit.edu/klmitch/Sipb/devel/src/ircu2.10.11/doc/p10.html (incomplete)


# include(s):

import hashlib
import socket
import time


# JupeServ Command(s):

def parse_jupeserv_command(command, data):
    JUPESERV_COMMANDS[command](data)

def parse_jupeserv_auth(data):
    # AUTH <account> <password>

    if is_channel(data[2]) == True:
        sendString(data[0], JUPESERV_ERR_NOTPUBLIC)
        return
    if data[2] != JUPESERV_SECURE:
        sendString(data[0], JUPESERV_ERR_USESECURE)
        return
    if is_array(data, 5) == False:
        sendString(data[0], JUPESERV_ERR_NEEDMOREARGS)
        return
    if data[0] in JUPESERV_AUTHED:
        sendString(data[0], "You are already authed.")
        return
    account = data[4].lower()
    if account not in JUPESERV_USERS:
        sendString(data[0], "That account does not exist.")
        return
    password = data[5].strip(NEW_LINES)
    password = "(" + str(JUPESERV_SALT) + ":" + password + ")"
    password = password.encode("UTF-8")
    output = hashlib.sha512(password).hexdigest().lower()
    if JUPESERV_USERS[account] != output:
        sendString(data[0], "That password is incorrect.")
        return
    JUPESERV_AUTHED.append(data[0])
    sendString(data[0], "You are now authed.")

def parse_jupeserv_help(data):
    # HELP

    sendString(data[0], "The following command(s) are available.")
    sendString(data[0], "----------------------------------------")
    for item in JUPESERV_COMMANDS:
        string = item + " " + JUPESERV_COMMANDS_HELP[item]
        sendString(data[0], string)

def parse_jupeserv_mkpasswd(data):
    # MKPASSWD <input>

    if is_channel(data[2]) == True:
        sendString(data[0], JUPESERV_ERR_NOTPUBLIC)
        return
    if data[2] != JUPESERV_SECURE:
        sendString(data[0], JUPESERV_ERR_USESECURE)
        return
    if len(data[3:]) == 1:
        sendString(data[0], JUPESERV_ERR_NEEDMOREARGS)
        return
    userInput = data[4].strip(NEW_LINES)
    userInput = "(" + str(JUPESERV_SALT) + ":" + userInput + ")"
    userInput = userInput.encode("UTF-8")
    output = hashlib.sha512(userInput).hexdigest().lower()
    sendString(data[0], "Hash: " + output)

def parse_jupeserv_raw(data):
    # RAW <args>

    if data[0] not in JUPESERV_AUTHED:
        sendString(data[0], JUPESERV_ERR_ACCESSDENIED)
        return
    if len(data[3:]) == 1:
        sendString(data[0], JUPESERV_ERR_NEEDMOREARGS)
        return
    sendLine = " ".join(data[4:])
    sendRaw("{}{}".format(sendLine, NEW_LINES))
    if is_channel(data[2]) == False:
        sendRaw("{} P {} :[{}] {}{}".format(JUPE_NUMERIC, JUPESERV_CHAN, data[0], sendLine, NEW_LINES))
        # `-> Prevent abuse. (Although this will tell you the numeric of the user, not the nick.)
    sendString(data[0], JUPESERV_RPL_DONE)


# P10/Server Function(s):

def parse_P10_command(command, data):
    P10_COMMANDS[command](data)

def parse_P10_info(data):
    # <numeric> <F|INFO> <server numeric>

    data = data.split(" ")
    sendRaw("{} 371 {} :{}{}".format(JUPE_NUMERIC, data[0], JUPE_NAME, NEW_LINES))
    sendRaw("{} 371 {} :{}{}".format(JUPE_NUMERIC, data[0], JUPE_INFO, NEW_LINES))
    sendRaw("{} 374 {} :{}{}".format(JUPE_NUMERIC, data[0], RPL_ENDOFINFO, NEW_LINES))

def parse_P10_kill(data):
    # <numeric> <D|KILL> <target numeric> :<reason>

    line = data.split(" ")
    if line[2] in JUPESERV_AUTHED:
        JUPESERV_AUTHED.remove(line[2])

def parse_P10_motd(data):
    # <numeric> MO[TD] <server numeric>

    sendRaw("{} 422 {} :{}{}".format(JUPE_NUMERIC, data.split(" ")[0], ERR_NOMOTD, NEW_LINES))

def parse_P10_ping(data):
    # <numeric> <G|PING> [:]<arg>

    sendRaw("{} Z {}{}".format(JUPE_NUMERIC, data.split(" ")[2], NEW_LINES))
    # `-> Saying PONG instead of Z should also work; but let's just leave it alone.

def parse_P10_privmsg(data):
    # <numeric> P[RIVMSG] <target> :<message>
    #
    # Note: Target will either be a channel, numeric, or <bot>@<server>. (So any multi-target messages are split over several lines.)

    line = data.split(" ")
    command = line[3][1:].lower()
    command = command.strip(NEW_LINES)
    # ¦-> So, when regular users get raw data on bircd, there isn't any \n on the end of a PRIVMSG line.
    # ¦-> However, with servers, this is a completely different story. There is an \n appended to the end of the line.
    # `-> As a result of this mild annoyance, I'm stripping NEW_LINES from the command name.
    if line[2] != JUPESERV_NUMERIC and line[2] != JUPESERV_SECURE:
        if command[0] != JUPESERV_TRIGGER:
            return
        command = command[1:]
    if command not in JUPESERV_COMMANDS:
        if line[2] == JUPESERV_NUMERIC:
            sendString(line[0], JUPESERV_ERR_NOSUCHCOMMAND.format(command))
        return
    parse_jupeserv_command(command, line)

def parse_P10_quit(data):
    # <numeric> Q[UIT] :[quit message]

    line = data.split(" ")
    if line[0] in JUPESERV_AUTHED:
        JUPESERV_AUTHED.remove(line[0])

def parse_P10_time(data):
    # <numeric> TI[ME] <server numeric>

    sendRaw("{} 391 {} {}{}".format(JUPE_NUMERIC, data.split(" ")[0], RPL_TIME.format(JUPE_NAME, str(int(time.time())), 0, time.strftime("%A %B %d %Y -- %H:%M:%S %z")), NEW_LINES))
    # `-> 0 is offset. I don't know what to put here, so I'm leaving it as zero.


# Function(s):

def base64toint(numeric):
    """Convert a base64 numeric to a number. E.g. base64toint("Qz]")"""
    o = 0
    x = 1
    while mid(numeric, x, 1):
        o = (o * 64)
        o = (o + i(mid(numeric, x, 1)))
        x += 1
    return o

def binaryAnd(A, B):
    """Returns A binary and B."""
    return int(A) & int(B)

def i(arg):
    P10_BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789[]"
    return P10_BASE64.find(arg)

def ii(arg):
    return mid("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789[]", (int(arg) + 1), 1)

def inttobase64(number, padding):
    """Convert a numeric number to base64 with the specified padded length. E.g. inttobase64(482, 2)"""
    c = padding
    o = ""
    v = number
    while c:
        o = ii(binaryAnd(v,63)) + o
        v = (v / 64)
        c -= 1
    return o
# [6]

def is_array(array, index):
    """Returns true or false depending on if an index exists within an array."""
    try:
        array[index]
    except IndexError:
        return False
    return True

def is_channel(channel):
    """Returns true or false depending on if the input is a channel."""
    if channel[0] == "#":
        return True
    return False

def mid(string, offset, amount):
    return string[offset-1:offset+amount-1]
# `-> Credit where credit is due, this is by Stanton Attree on Stack Overflow.

def sendRaw(data):
    jupe.send(data.encode("UTF-8"))
    print(data.strip(NEW_LINES))

def sendString(numeric, string):
    sendRaw("{} {} {} :{}{}".format(JUPESERV_NUMERIC, JUPESERV_REPLY_METHOD, numeric, string, NEW_LINES))


# define(s):

JUPESERV_AUTHED = []
# `-> Leave this blank. The bot will handle this. (NOTE: Not currently handled by SQ[UIT].)
JUPESERV_CHAN = "#JupeServ"
JUPESERV_BOT = "JupeServ"
# [7]
JUPESERV_TRIGGER = "?"
JUPESERV_ENABLED = 1
JUPESERV_REPLY_METHOD = "O"
# `-> This is a NOTICE (P10 = O). If you want PRIVMSG, use P. (PRIVMSG works too.)
JUPESERV_SALT = "changeme"
JUPESERV_USERS = {
    "changeme": "a5eb61c9170a54325ee8c75d74611a721cb9a782d4d2ead1b808f430c8568b333c51b180eff98f0113d0b2e9fb70c9bc6b991ce91c02041eecc9820c55113f73"
}
# ¦-> Names and sha512 passwords must be in lowercase. To use this, connect to the IRCd and type: /msg <bot>@<server> MKPASSWD <password>
# ¦-> Then use the hash that was generated in here.
# `-> The hash is unsalted 128 character junk input, by the way.

JUPESERV_COMMANDS = {
    "auth": parse_jupeserv_auth,
    "help": parse_jupeserv_help,
    "mkpasswd": parse_jupeserv_mkpasswd,
    "raw": parse_jupeserv_raw
}
JUPESERV_COMMANDS_HELP = {
    "auth": "- AUTH <account> <password> (Auth to {} to use RAW.)".format(JUPESERV_BOT),
    "help": "- HELP (Lists all available commands.)",
    "mkpasswd": "- MKPASSWD <input> (Encrypts a string for password use.)",
    "raw": "- RAW <args> (Send raw args. This requires knowledge of what you're doing.)"
}
# `-> /msg <bot> HELP

JUPE_FLAGS = "+s"
# `-> Append flags - which in this case is basically just 6 or s (or both) - with +. If no flags are specified, just leave it as: +
JUPE_INFO = "A jupe server for ircu P10 protocol in Python."
JUPE_INT_NUMERIC = 0
# `-> The numeric of our server. Limited between 0 and 4095.
JUPE_PASSWORD = "changeme"
# `-> Plaintext password.
JUPE_PORT = 4400
# `-> The port for the server we plan on connecting to.
JUPE_SERVER = "localhost"
# `-> The address we plan on connecting to. E.g. /server localhost 4400
JUPE_NAME = "changeme.localhost"
# `-> The name of our server.

P10_COMMANDS = {
    "D": parse_P10_kill,
    "INFO": parse_P10_info,
    "F": parse_P10_info,
    "G": parse_P10_ping,
    "KILL": parse_P10_kill,
    "MO": parse_P10_motd,
    "MOTD": parse_P10_motd,
    "P": parse_P10_privmsg,
    "PING": parse_P10_ping,
    "PRIVMSG": parse_P10_privmsg,
    "Q": parse_P10_quit,
    "QUIT": parse_P10_quit,
    "TI": parse_P10_time,
    "TIME": parse_P10_time
}
# `-> Cover both LONG and S[HORT] names since both are acceptable.

JUPE_NUMERIC = inttobase64(JUPE_INT_NUMERIC, 2)
# `-> Convert our numeric to the base64 name for use in specific sendRaw() responses.
JUPESERV_NUMERIC = JUPE_NUMERIC + "AAA"
JUPESERV_SECURE = JUPESERV_BOT + "@" + JUPE_NAME
# `-> For /msg <bot>@<server> ...
JUPE_EPOCH = str(int(time.time()))

ERR_NOMOTD = "MOTD File is missing"
RPL_ENDOFINFO = "End of /INFO list."
RPL_TIME = "{} {} {} :{}"

JUPESERV_ERR_ACCESSDENIED = "You do not have permission to use this command."
JUPESERV_ERR_NEEDMOREARGS = "Insufficient parameters."
JUPESERV_ERR_NOSUCHCOMMAND = "The command [{}] does not exist."
JUPESERV_ERR_NOTPUBLIC = "Security violation. You may not use this command publicly."
JUPESERV_ERR_USESECURE = "Security violation. Please /msg {} <command> [args] instead.".format(JUPESERV_SECURE)
JUPESERV_RPL_DONE = "Done."

NEW_LINES = "\r\n"

jupe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
jupe.connect((JUPE_SERVER, JUPE_PORT))

# Core:

def main():
    sendRaw("PASS :{}{}".format(JUPE_PASSWORD, NEW_LINES))
    # `-> PASS must _ALWAYS_ come first.
    sendRaw("SERVER {} 1 {} {} J10 {}]]] {} :{}{}".format(JUPE_NAME, JUPE_EPOCH, JUPE_EPOCH, JUPE_NUMERIC, JUPE_FLAGS, JUPE_INFO, NEW_LINES))
    # ¦-> SERVER <our server name> <hop count> <connection time> <link time> <protocol> <our server numeric><max users as numeric> [+flags] :<description>
    # ¦
    # ¦-> We're joining the server, so we use J10, not P10. And ]]] means the maximum number of users allowed. (262,143)
    # ¦-> Flags may or may not being used here; but +s would mean Services. E.g. ... J10 SV]]] +s :IRC Services
    # `-> NOTE: In case of adding a new server post END_OF_BURST, flags must be specified! Even if it's just + otherwise the server _WILL_ SQUIT.
    if JUPESERV_ENABLED == 1:
        sendRaw("{} N {} 1 {} {} {} +iko {} {} :{}{}".format(JUPE_NUMERIC, JUPESERV_BOT, JUPE_EPOCH, JUPESERV_BOT, JUPE_NAME, inttobase64(2130706433, 6), JUPESERV_NUMERIC, JUPESERV_BOT, NEW_LINES))
        # ¦-> <numeric> N[ICK] <hop count> <timestamp> <user> <host> [+modes] [modeargs ...] <ip as base64 numeric> <numeric> :<real name>
        # ¦
        # `-> Here, we create a user on the server.
        sendRaw("{} B {} {} +inst {}:o{}".format(JUPE_NUMERIC, JUPESERV_CHAN, JUPE_EPOCH, JUPESERV_NUMERIC, NEW_LINES))
        # ¦-> Initial:  <numeric> B[URST] <#channel> <timestamp> [+modes] [modeargs ...] <numeric[:status>[,<numeric[:status>],...]] [:%n!u@h n!u@h ...]
        # ¦-> Overflow: <numeric> B[URST] <#channel> <timestamp> [{numeric[:status}[,{numeric[:status}],...]] [:%n!u@h n!u@h ...]
        # ¦
        # ¦-> "Create" a channel upon connection. This line pretends that the channel already exists, and we're just BURSTing that information.
        # ¦-> However, if the channel already exists, the older timestamp takes priority. (So in that case the bot won't be opped.)
        # `-> Interesting sideline here, topics are not sent on bursting.
    sendRaw("{} EB{}".format(JUPE_NUMERIC, NEW_LINES))
    # `-> END_OF_BURST

    while 1:
        data = jupe.recv(4096).decode("UTF-8")
        if not data:
            break
        print(data)
        if len(data.strip(NEW_LINES)) == 0:
            return
        newData = data.split(NEW_LINES)
        for line in newData:
            newLine = line.split(" ")
            if len(newLine) > 1:
                if newLine[1] in P10_COMMANDS:
                    parse_P10_command(newLine[1], line)
            if newLine[0] in P10_COMMANDS:
                parse_P10_command(newLine[0], line)
    jupe.close()
    print("Socket closed.\n")
    # JUPESERV_AUTHED.clear()
    # `-> Probably redundant.

if __name__ == "__main__":
    main()


# Footnote(s):
# ---------------
# [1]: C:127.0.0.1:changeme:changeme.localhost::0 in an ircd.conf
# [2]: Example only. Factors like the numeric of the main server (AA, AB, etc.) will change this. (AAAAx, ABAAx, ACAAx, etc.)
#      You'll be able to tell what the numeric of the main server is from B information on linking. (Or hopefully from doing /map.)
# [3]: This example is operating under the assumption that you don't fiddle with the numeric number above. (0)
# [4]: AAAAA on top of AAAAA will result in a numeric collision (thus SQUIT). However, making "AAAAA Q :Quit." first is fine.
# [5]: I honestly fail to see how a server inviting a user to a channel is a problem. (They can change modes, kick users, talk,
#      all without being on the channel. So why can't they invite anybody?)
# [6]: Thanks to Dave (Codex` / Hero_Number_Zero) for once sharing the numeric/P10 conversion code with me nearly a decade ago. (Ported to Python.)
# [7]: If you're worried about the name being used, use a U:line in the ircd.conf. E.g. U:changeme.localhost:JupeServ:
#
# EOF
