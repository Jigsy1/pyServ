# pyServer.py - An example of linking to an ircu based IRCd in Python.
#
# This script will not work unless you have a C:line[1] on an ircu based IRCd. (http://ircd.bircd.org/)
#
# Sadly, unlike the mSL jupe I wrote, there isn't any way for you to be able to send raw commands natively due to the while loop.
# However, I might update this to allow a juped user that allows raw commands to be sent.
#
# Further reading:
# --------------------
# 1. [P10]:  http://ircd.bircd.org/bewarep10.txt (recommended)
# 2. [P10]:  https://web.archive.org/web/20100209040721/http://www.xs4all.nl/~carlo17/irc/P10.html
# 3. [Raws]: https://modern.ircdocs.horse/index.html
# 4. [P10]:  http://web.mit.edu/klmitch/Sipb/devel/src/ircu2.10.11/doc/p10.html (incomplete)


# include(s):

import socket
import time


# P10/Server Function(s):

def parse_P10_command(command, data):
    P10_COMMANDS[command](data)

def parse_P10_info(data):
    # `-> <numeric> <F|INFO> <server numeric>

    data = data.split(" ")
    sendRaw("{} 371 {} :{}{}".format(JUPE_BASENUM, data[0], JUPE_NAME, NEW_LINES))
    sendRaw("{} 371 {} :{}{}".format(JUPE_BASENUM, data[0], JUPE_INFO, NEW_LINES))
    sendRaw("{} 374 {} :End of /INFO list.{}".format(JUPE_BASENUM, data[0], NEW_LINES))

def parse_P10_motd(data):
    # `-> <numeric> MO[TD] <server numeric>

    sendRaw("{} 422 {} :{}{}".format(JUPE_BASENUM, data.split(" ")[0], ERR_NOMOTD, NEW_LINES))

def parse_P10_ping(data):
    # `-> <numeric> <G|PING> [:]<arg>

    sendRaw("{} Z {}{}".format(JUPE_BASENUM, data.split(" ")[2], NEW_LINES))
    # `-> Saying PONG instead of Z should also work; but let's just leave it alone.

def parse_P10_time(data):
    # `-> <numeric> TI[ME] <server numeric>

    sendRaw("{} 391 {} {}{}".format(JUPE_BASENUM, data.split(" ")[0], RPL_TIME.format(JUPE_NAME, str(int(time.time())), 0, time.strftime("%A %B %d %Y -- %H:%M:%S %z")), NEW_LINES))
    # `-> 0 is offset. I don't know what to put here, so I'm leaving it as zero.


# Function(s):

def mid(string, offset, amount):
    return string[offset-1:offset+amount-1]
# `-> Credit where credit is due, this is by Stanton Attree on Stack Overflow.

def base64toint(input):
    """Convert a base64 numeric to a number. E.g. base64toint("Qz]")"""
    o = 0
    x = 1
    while mid(input, x, 1):
        o = (o * 64)
        o = (o + i(mid(input, x, 1)))
        x += 1
    return o

def binaryAnd(A, B):
    """Returns A binary and B."""
    return int(A) & int(B)

def i(input):
    P10_BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789[]"
    return P10_BASE64.find(input)

def ii(input):
    return mid("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789[]", (int(input) + 1), 1)

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
# [2]

def sendRaw(input):
    jupe.send(input.encode("UTF-8"))
    print(input.strip(NEW_LINES))


# define(s):

JUPE_FLAGS = "+"
# `-> Append flags - which in this case is basically just 6 or s (or both) - with +. If no flags are specified, just leave it as: +
JUPE_INFO = "A jupe server for ircu P10 protocol in Python."
JUPE_NUMERIC = 0
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
    "INFO": parse_P10_info,
    "F": parse_P10_info,
    "G": parse_P10_ping,
    "MO": parse_P10_motd,
    "MOTD": parse_P10_motd,
    "PING": parse_P10_ping,
    "TI": parse_P10_time,
    "TIME": parse_P10_time
}
# `-> Cover both LONG and SHORT names.

ERR_NOMOTD = "MOTD File is missing"
RPL_TIME = "{} {} {} :{}"

NEW_LINES = "\r\n"

jupe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
jupe.connect((JUPE_SERVER, JUPE_PORT))

JUPE_BASENUM = inttobase64(JUPE_NUMERIC, 2)
# `-> Convert our numeric to the base64 name for use in specific sendRaw() responses.
JUPE_EPOCH = str(int(time.time()))


# Core:

def main():
    sendRaw("PASS :{}{}".format(JUPE_PASSWORD, NEW_LINES))
    # `-> PASS must _ALWAYS_ come first.
    sendRaw("SERVER {} 1 {} {} J10 {}]]] {} :{}{}".format(JUPE_NAME, JUPE_EPOCH, JUPE_EPOCH, JUPE_BASENUM, JUPE_FLAGS, JUPE_INFO, NEW_LINES))
    # ¦-> SERVER <our server name> <hop count> <connection time> <link time> <protocol> <our server numeric><max users as numeric> [+flags] :<description>
    # ¦-> We're joining the server, so we use J10, not P10. And ]]] means the maximum number of users allowed. (262,143)
    # ¦-> Flags may or may not being used here; but +s would mean Services. E.g. ... J10 SV]]] +s :IRC Services
    # `-> NOTE: In case of adding a new server post END_OF_BURST, flags must be specified! Even if it's just + otherwise the server _WILL_ SQUIT.
    sendRaw("{} EB{}".format(JUPE_BASENUM, NEW_LINES))
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

if __name__ == "__main__":
    main()


# Footnote(s):
# [1]: C:127.0.0.1:changeme:changeme.localhost::0 in an ircd.conf
# [2]: Thanks to Dave (Codex` / Hero_Number_Zero) for once sharing the numeric/P10 conversion code with me nearly a decade ago. (Ported to Python.)
#
# EOF
