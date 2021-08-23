from wikitools import *
import time
import urllib
import json
import userpassbot  # Bot password
import warnings
import re
import mwparserfromhell
import datetime
import sys
import RSconfig

site = wiki.Wiki()  # Tell Python to use the English Wikipedia's API
site.login(userpassbot.username, userpassbot.password)  # login

# namespace 3 is the user talk namespace
namespaces = "0|1|2|4|5|6|7|8|9|10|11|12|13|14|15|90|91|92|93|100|101|102|103|104|105|106|107|486|487|828|829|1198|1199|2600|5500|5501"

# routine to autoswitch some of the output - as filenames have accented chars!
def pnt(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('utf-8'))


def start_allowed():
    textpage = page.Page(site, "User:TheSandBot/status").getWikiText()
    data = json.loads(textpage)["run"]["restrict_clerking"]
    if str(data) == str(True):
        return True
    return False


def allow_bots(text, user):
    user = user.lower().strip()
    text = mwparserfromhell.parse(text)
    for tl in text.filter_templates():
        if tl.name.matches(['bots', 'nobots']):
            break
    else:
        return True
    print("template found")  # Have we found one
    for param in tl.params:
        bots = [x.lower().strip() for x in param.value.split(",")]
        if param.name == 'allow':
            print("We have an ALLOW")  # allow found
            if ''.join(bots) == 'none': return False
            for bot in bots:
                if bot in (user, 'all'):
                    return True
        elif param.name == 'deny':
            print("We have a DENY")  # deny found
            if ''.join(bots) == 'none':
                print("none - true")
                return True
            for bot in bots:
                if bot in (user, 'all'):
                    pnt(bot)
                    pnt(user)
                    print("all - false")
                    return False
    if tl.name.matches('nobots') and len(tl.params) == 0:
        print("match - false")
        return False
    return True


def str_to_date(date_str):
    timestamp = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
    return timestamp


def YoungestDate(date_in):
    date_in = str_to_date(date_in)
    if date_in > RSconfig.mydate:
        RSconfig.mydate = date_in
        RSconfig.validuser = True
    return


def get_last_contrib(user):
    params = {'action': 'query',
              'list': 'usercontribs',
              'uclimit': 1,
              'ucuser': user,
              'ucdir': "older",
              'ucnamespace': namespaces
              }
    # print "GLC.params"
    request = api.APIRequest(site, params)  # Set the API request
    # print "GLC.request"
    result = request.query(False)
    # print result, len(result)
    if len(result) > 2:
        founddate = date = result['query']['usercontribs'][0]['timestamp']
        print("Last Normal Edit", str_to_date(founddate))
        YoungestDate(founddate)
    else:
        print("No normal contrib")
    return


def GetLastDeleted(user):
    params = {'action': 'query',
              'list': 'alldeletedrevisions',
              'adrprop': 'timestamp',
              'adrlimit': 1,
              'adruser': user,
              'adrdir': "older",
              'adrnamespace': namespaces
              }
    # print "GLD.params"
    request = api.APIRequest(site, params)  # Set the API request
    # print "GLD.request"
    result = request.query(False)
    # print result, len(result)
    if len(result) > 2:
        try:
            founddate = result['query']['alldeletedrevisions'][0]['revisions'][0]['timestamp']
            print("Last Deleted Edit", str_to_date(founddate))
            YoungestDate(founddate)
        except IndexError:
            pass # bad page title, move on. This was discovered Aug 22 2021 with Doc James
    else:
        print("No deleted contrib")
    return


def examine_user(user):
    if len(user) > 0:
        get_last_contrib(user)
        GetLastDeleted(user)
    return


def find_users(text):
    RSconfig.movetab = False
    RSconfig.mydate = str_to_date("2000-01-01T00:00:00Z")  # new lot of user, set mydate to way back.
    RSconfig.validuser = False
    usertext = re.sub(r'![\s]*?[Ss]cope="row"[\s\S]*?\|', "", text)  # remove column 1
    bracket = 0  # now find end of column 2
    for x in range(0, len(usertext) - 1):
        s = usertext[x]
        found = 1
        if s == "|":
            found = 0
        if bracket + found == 0:
            enduser = x
            break
        if s == "[":
            bracket = bracket + 1
        if s == "]":
            bracket = bracket - 1
        if s == "{":
            bracket = bracket + 1
        if s == "}":
            bracket = bracket - 1
    textcol2 = usertext[0:enduser]  # this is all column 2 - above code ignores "|" inside [|] or {|}
    expirydate = datetime.datetime.utcnow() + datetime.timedelta(days=365)
    for match in re.finditer(r'\[\[[Uu]ser:[\s\S]*?[\|\]]', textcol2):  # [User:XXXX]
        user = textcol2[match.start() + 2:match.end() - 1]
        colon = user.index(":")
        user = user[colon + 1:]
        pnt("UserA =" + user)
        if "username" not in user.lower():
            examine_user(user)
    for match in re.finditer(r'\{\{[Uu]\|[\s\S]*?\}\}', textcol2):  # {{U:XXXX}}
        user = "User:" + textcol2[match.start() + 4:match.end() - 2]
        colon = user.index(":")
        user = user[colon + 1:]
        pnt("UserB =" + user)
        if "username" not in user.lower():
            examine_user(user)
    for match in re.finditer(r'\{\{[Nn]oping\|[\s\S]*?\}\}', textcol2):  # {{noping|XXXX}}
        user = "User:" + textcol2[match.start() + 9:match.end() - 2]
        colon = user.index(":")
        user = user[colon + 1:]
        pnt("UserC =" + user)
        if "username" not in user.lower():
            examine_user(user)
    if "dynamic" in textcol2.lower():  # Dynamic
        print("DYNAMIC FLAG")
        RSconfig.mydate = datetime.datetime.utcnow()
    if RSconfig.validuser:
        mylist = []
        textlen = len(usertext) - 1
        print("textlen", textlen)
        for x in range(textlen, 0, -1):
            if usertext[x] == "|":
                mylist.append(x)
        print(mylist)  # mylist[1] to end is final column
        textlastcol = usertext[mylist[1]:]
        textlastcollow = textlastcol.lower()
        if textlastcollow.find("indefinite") >= 0:
            print(expirydate)
        else:
            datefound = re.findall(r'20\d\d[\s-]\d\d[\s-]\d\d', textlastcol)
            if len(datefound) > 0:
                expirydate = str_to_date(datefound[0] + "T00:00:00Z")
        print("Last Group Edit", RSconfig.mydate)
        print("ExpiryDate", expirydate)
        if not RSconfig.archive:
            if RSconfig.mydate < datetime.datetime.utcnow() - datetime.timedelta(days=730):
                print("THIS ROW TO BE ARCHIVED - EDITS TWO YEARS OLD")
                RSconfig.movetab = True
            if expirydate < datetime.datetime.utcnow():
                print("THIS ROW TO BE ARCHIVED - EXPIRED DATE")
                RSconfig.movetab = True
        else:
            if expirydate > datetime.datetime.utcnow():
                if RSconfig.mydate > datetime.datetime.utcnow() - datetime.timedelta(days=730):
                    print("THIS ROW TO BE UN ARCHIVED - NOT EXPIRED, and NEW EDITS")
                    RSconfig.movetab = True
    return


def move_to_dest(startp, endp, text):
    print("MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM")
    print(len(text))
    print(len(RSconfig.pagetext))
    # tabline1=text[startp:endp]
    tabline = RSconfig.pagetext[startp:endp]
    print(tabline)
    print("****************")
    pagetext = RSconfig.pagetext[0:startp - 1] + "\n\n" + RSconfig.pagetext[endp + 1:]
    RSconfig.pagetext = pagetext
    print(repr(tabline))
    print("MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM")
    pagetext = RSconfig.destpagetext[0:RSconfig.insert] + "\n\n" + tabline + "\n\n" + RSconfig.destpagetext[
                                                                                      RSconfig.insert + 1:]
    RSconfig.destpagetext = pagetext
    return


def check_tab(start, end, text):
    RSconfig.movetab = False
    print(start, end)
    tabline = text[start:end]
    print(repr(tabline))
    print("++++++++++++++++++++++++++Start of Table Section+++++++++++++++++++++++++++++++++++++++")
    print(repr(tabline))
    print("++++++++++++++++++++++++++End of Table Section+++++++++++++++++++++++++++++++++++++++")
    find_users(tabline)
    print("==========================End of Section Data=======================================")
    if RSconfig.movetab:
        print("Eliminate", start, end)
        move_to_dest(start, end, text)
        RSconfig.changed = +1
    return


def process_page(subpage):
    RSconfig.changed = 0
    RSconfig.origpage = subpage
    # set to get the two pages
    if RSconfig.archive:
        RSconfig.pagename = RSconfig.nameprefix + "/Archive/" + subpage
        RSconfig.destpagename = RSconfig.nameprefix + "/" + RSconfig.origpage
        editsum = "([[Wikipedia:Bots/Requests for approval/TheSandBot 9|Task 9]]) Active Users - Remove from " \
                  "Archive to go to [[" + RSconfig.destpagename + "]]"
        editsumdest = "([[Wikipedia:Bots/Requests for approval/TheSandBot 9|Task 9]]) Active Users - Returning " \
                      "from Archive ([[" + RSconfig.pagename + "]])"
    else:
        RSconfig.pagename = RSconfig.nameprefix + "/" + RSconfig.origpage
        RSconfig.destpagename = RSconfig.nameprefix + "/Archive/" + subpage
        editsum = "([[Wikipedia:Bots/Requests for approval/TheSandBot 9|Task 9]]) Inactive Users - Remove to archive " \
                  "([[" + RSconfig.destpagename + "]])"
        editsumdest = "([[Wikipedia:Bots/Requests for approval/TheSandBot 9|Task 9]]) Inactive Users - Add to " \
                      "Archive from [[" + RSconfig.pagename + "]]"
    print(RSconfig.pagename)
    print(RSconfig.destpagename)
    RSconfig.pagepage = page.Page(site, RSconfig.pagename)
    print(RSconfig.pagepage.title)
    RSconfig.pagetext = RSconfig.pagepage.getWikiText()
    RSconfig.pagesize = len(RSconfig.pagetext)
    RSconfig.destpagepage = page.Page(site, RSconfig.destpagename)
    RSconfig.destpagetext = RSconfig.destpagepage.getWikiText()
    RSconfig.destpagesize = len(RSconfig.destpagetext)
    print("Page Sizes from and to", RSconfig.pagesize, RSconfig.destpagesize)
    # Check pages for nobots - unlikly to be here
    stop = allow_bots(RSconfig.pagetext, "TheSandBot")
    if not stop:
        return
    stop = allow_bots(RSconfig.destpagetext, "TheSandBot")
    if not stop:
        return
    # find the table start and the table end
    tabtop = RSconfig.pagetext.find('{|') - 1
    tabbot = RSconfig.pagetext.rfind('|}') - 1
    desttabtop = RSconfig.destpagetext.find('{|') - 1
    desttabbot = RSconfig.destpagetext.rfind('|}') - 1
    # Fix the table end to a new row start and space out the table rows
    RSconfig.pagetext = RSconfig.pagetext[0:tabbot] + '\n|-\n! scope="row"\nBOTEND' + RSconfig.pagetext[tabbot + 1:]
    RSconfig.destpagetext = RSconfig.destpagetext[0:desttabbot] + '\n|-\n! scope="row"\nBOTEND' + RSconfig.destpagetext[
                                                                                                  desttabbot + 1:]
    RSconfig.pagetext = re.sub(r'\|-\n!', '|-\n\n!', RSconfig.pagetext)
    RSconfig.destpagetext = re.sub(r'\|-\n!', '|-\n\n!', RSconfig.destpagetext)
    # Get the table row starts
    destpositionlist = []
    for match in re.finditer(r'(!)[\s]*?[Ss]cope="row"', RSconfig.destpagetext):
        end = match.start() - 1
        if end > desttabtop:
            destpositionlist.append(end)
    RSconfig.insert = destpositionlist[0] - 1  # Insert point is everything before the first "!"
    positionlist = []
    for match in re.finditer(r'(!)[\s]*?[Ss]cope="row"', RSconfig.pagetext):
        end = match.start() - 1
        if end > tabtop:
            positionlist.append(end)
    # Final match is positionlist[len(positionlist)-1]
    rows = len(positionlist)
    end = positionlist[rows - 1]  # end of table marker (dummy row start put in earlier)
    print(end)
    for a in range(rows - 2, 0, -1):  # MAIN Loop to check each tabline in reverse order
        start = positionlist[a]
        print(start, RSconfig.pagetext[start])  # all are "!"
        check_tab(start, end, RSconfig.pagetext)
        end = start - 1
        RSconfig.lastrow = False
    if RSconfig.changed > 0:
        # Need to restore the correct table end, and remove excess blank lines added
        print("====================")
        RSconfig.pagetext = re.sub(r'\|-\n*?! scope="row"\nBOTEND\|\}', '|}', RSconfig.pagetext)
        RSconfig.pagetext = re.sub(r'\|-\n*?\!', '|-\n!', RSconfig.pagetext)
        print(RSconfig.pagetext)
        RSconfig.destpagetext = re.sub(r'\|-\n*?! scope="row"\nBOTEND\|\}', '|}', RSconfig.destpagetext)
        RSconfig.destpagetext = re.sub(r'\|-\n*?\!', '|-\n!', RSconfig.destpagetext)
        print(RSconfig.destpagetext)
        print("TIME TO CHECK FROM PAGE")
        # Get current page sizes - has someone edited while processing? - check with saved size on first load
        pagepage = page.Page(site, RSconfig.pagename)
        pagetext = pagepage.getWikiText()
        pagesize = len(pagetext)
        if pagesize != RSconfig.pagesize:
            print("Page Has been edited - aborting")
            return
        print("TIME TO CHECK DEST PAGE")
        destpagepage = page.Page(site, RSconfig.destpagename)
        destpagetext = destpagepage.getWikiText()
        destpagesize = len(destpagetext)
        if destpagesize != RSconfig.destpagesize:
            print("Page Has been edited abort")
            return
        RSconfig.pagepage.edit(text=RSconfig.pagetext, bot=True,
                               summary=editsum)  # (DO NOT UNCOMMENT UNTIL BOT IS APPROVED)
        RSconfig.destpagepage.edit(text=RSconfig.destpagetext, bot=True,
                                   summary=editsumdest)  # (DO NOT UNCOMMENT UNTIL BOT IS APPROVED)
        print("====================")
    else:
        print("NO CHANGES TO PAGE NEEDED")
    return


def main():
    RSconfig.nameprefix = "Wikipedia:Editing restrictions"
    if not start_allowed():  # Check if task is enabled
        sys.exit('Disabled Task')
    # parameters for API request
    print("main is go")
    # Send each subpage in turn
    RSconfig.archive = False
    print("####################################################################")
    print("Process - Wikipedia:Editing restrictions/Placed by the Arbitration Committee")
    process_page('Placed by the Arbitration Committee')
    print("####################################################################")
    print("Wikipedia:Editing restrictions/Placed by the Wikipedia community")
    process_page('Placed by the Wikipedia community')
    print("####################################################################")
    print("Wikipedia:Editing restrictions/Voluntary")
    process_page('Voluntary')
    print("####################################################################")
    print("Wikipedia:Editing restrictions/Unblock conditions")
    process_page('Unblock conditions')
    RSconfig.archive = True
    print("####################################################################")
    print("Process - Wikipedia:Editing restrictions/Archive/Placed by the Arbitration Committee")
    process_page('Placed by the Arbitration Committee')
    print("####################################################################")
    print("Wikipedia:Editing restrictions/Archive/Placed by the Wikipedia community")
    process_page('Placed by the Wikipedia community')
    print("####################################################################")
    print("Wikipedia:Editing restrictions/Archive/Voluntary")
    process_page('Voluntary')
    print("####################################################################")
    print("Wikipedia:Editing restrictions/Archive/Unblock conditions")
    process_page('Unblock conditions')


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        main()
