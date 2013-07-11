# Grabs N people randomly from the directory using reservoir sampling, then
# counts the number of followers they have.

import mechanize
import random
import cookielib
import re
from time import sleep

NUM_SAMPLES = 1000
FOLLOWERS_FILE = "followers.txt"
USERS_FILE = "users.txt"
ERR_LOG = "errors.txt"

err = open(ERR_LOG, 'w')

# Randomly chosen Quora users (written in the form of links to Quora
# profiles)
users = []
curUserIdx = 1

# Regular expressions that will be used multiple times
leaf = re.compile("-") # Separator between first and last names!
internalNode = re.compile("directory/page")
fnum = re.compile("Followers.*>([0-9]+)<.*Following")

# We use this function to open pages instead of openPage to avoid putting a
# high load on Quora's servers.  This means the script takes a lot longer
# though - estimated time 1 day for 2 million users.  (21400 page accesses
# * 4 seconds per access = 23.8 hours.)
def openPage(site):
    br.open(site)
    sleep(3)

# Gets child links
def getChildren(node):
    try:
        openPage(node)
        return ["http://www.quora.com" + link.url for link in br.links()]
    except:
        print "Could not get children of " + node
        err.write("Could not get children of " + node)
        return []

# Checks to see if the link is a user profile.
def isLeaf(node):
    return leaf.search(node)

# Checks to see if the link is an intermediate node in the directory.
def isInternalNode(node):
    return internalNode.search(node)

# Checks to see if the page is part of the people directory
def inPeopleDirectory(node):
    try:
        page = openPage(node)
        html = page.read()
    except:
        print "Could not open site " + node
        err.write("Could not open site " + node)
        return False

    return "People on Quora" in html

# Applies reservoir sampling to a candidate leaf
def sample(node):
    # curUserIdx is 1-indexed
    global users, curUserIdx
    # Initialize the list
    if (curUserIdx <= NUM_SAMPLES):
        users.append(node)

    # Replace elements
    else:
        # random.randint chooses a random integer, inclusive
        choice = random.randint(1, curUserIdx)
        if (choice <= NUM_SAMPLES):
            users[choice - 1] = node
    curUserIdx += 1

# Gets the number of followers for a user
def getFollowers(profile):
    try:
        page = openPage(profile)
        m = fnum.search(page.read())
        if m:
            return m.group(1)
    except:
        print "Could not get number of followers for " + profile
        err.write("Could not get number of followers for " + profile)

# Traverses the tree using depth first search.
def crawl(node):
    for child in getChildren(node):
        if child in excludedPages:
            pass
        elif isLeaf(child):
            print "Sampling " + child
            sample(child)
        elif isInternalNode(child):
            print "Crawling internal node " + child
            crawl(child)
        else:
            print "Passing on link " + child

# Initialize browser

br = mechanize.Browser()

cj = cookielib.LWPCookieJar()
br.set_cookiejar(cj)

br.set_handle_equiv(True)
br.set_handle_gzip(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)

# Follows refresh 0 but not hangs on refresh > 0
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

# User-Agent
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; \
rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

# Get list of top level pages (and exclude them from searches, because they
# form cycles)
excludedPages = filter(isInternalNode, getChildren("http://www.quora.com/directory"))
excludedPages.append("http://www.quora.com")
excludedPages.append("http://www.quora.com#")
excludedPages.append("http://www.quora.com/")
excludedPages.append("http://www.quora.com/about/tos")

topPages = filter(inPeopleDirectory, excludedPages)

# Access Quora directory (it's public access!)
for page in topPages:
    crawl(page)

# Get followers for each user
ff = open(FOLLOWERS_FILE, 'w')
uf = open(USERS_FILE, 'w')

# Write these in two separate steps in case something goes wrong with
# getFollowers.  I don't want to lose my random sample, because that is the
# hardest part to get.
for u in users:
    uf.write(u + "\n")
uf.close()

for u in users:
    numFollowers = getFollowers(u)
    if numFollowers:
        ff.write(u + "\t" + getFollowers(u) + "\n")

ff.close()
err.close()
