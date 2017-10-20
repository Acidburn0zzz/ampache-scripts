#!/usr/bin/env python3

""" query ampache mysql and merge into rhythmbox db

  merge data from ampache with rhythmbox
  --------------------------------------

  This script will examine a dump file from lastscrape
  then query your ampache database

  if it matches the artist, album and song
  it will update your databse to reflect each play

"""


# import codecs
import csv
import os
import shutil
# import sys
import mysql.connector
import urllib.parse
import xml.etree.ElementTree as etree


# Process/script checks
PROCESSPLAYS = None
PROCESSLOVED = None
WEHAVEMERGED = False
cnx = None
playcursor = None
ratingcursor = None

# File check
MERGEPLAYSFILE = False
MERGELOVEDFILE = False

# commandline arguments
OVERWRITEDUMP = False

# Default file names
settings = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.csv')

# Default paths for rhythmbox & the user
HOMEFOLDER = os.getenv('HOME')
PATH = '/.local/share/rhythmbox/'
DB = (HOMEFOLDER + PATH + 'rhythmdb.xml')
DBBACKUP = (HOMEFOLDER + PATH + 'rhythmdb-backup-merge.xml')

FIND = None
REPLACE = None

# get settings for database
if os.path.isfile(settings):
    print('found settings file')
    with open(settings, 'r') as csvfile:
        openfile = csv.reader(csvfile)
        for row in openfile:
            try:
                test = row[0]
            except IndexError:
                test = None
            if test:
                if row[0] == 'dbuser':
                    dbuser = row[1]
                elif row[0] == 'dbpass':
                    dbpass = row[1]
                elif row[0] == 'dbhost':
                    dbhost = row[1]
                elif row[0] == 'dbname':
                    dbname = row[1]
                elif row[0] == 'myid':
                    myid = row[1]
                elif row[0] == 'find':
                    FIND = row[1]
                elif row[0] == 'replace':
                    REPLACE = row[1]
    csvfile.close()
else:
    # Database variables
    dbuser = 'username'
    dbpass = 'password'
    dbhost = '127.0.0.1'
    dbname = 'database'

    # Ampache variables
    myid = '2'


urlascii = ('%', "#", ';', ' ', '"', '<', '>', '?', '[', '\\',
            "]", '^', '`', '{', '|', '}', '€', '‚', 'ƒ', '„',
            '…', '†', '‡', 'ˆ', '‰', 'Š', '‹', 'Œ', 'Ž', '‘',
            '’', '“', '”', '•', '–', '—', '˜', '™', 'š', '›',
            'œ', 'ž', 'Ÿ', '¡', '¢', '£', '¥', '|', '§', '¨',
            '©', 'ª', '«', '¬', '¯', '®', '¯', '°', '±', '²',
            '³', '´', 'µ', '¶', '·', '¸', '¹', 'º', '»', '¼',
            '½', '¾', '¿', 'À', 'Á', 'Â', 'Ã', 'Ä', 'Å', 'Æ',
            'Ç', 'È', 'É', 'Ê', 'Ë', 'Ì', 'Í', 'Î', 'Ï', 'Ð',
            'Ñ', 'Ò', 'Ó', 'Ô', 'Õ', 'Ö', 'Ø', 'Ù', 'Ú', 'Û',
            'Ü', 'Ý', 'Þ', 'ß', 'à', 'á', 'â', 'ã', 'ä', 'å',
            'æ', 'ç', 'è', 'é', 'ê', 'ë', 'ì', 'í', 'î', 'ï',
            'ð', 'ñ', 'ò', 'ó', 'ô', 'õ', 'ö', '÷', 'ø', 'ù',
            'ú', 'û', 'ü', 'ý', 'þ', 'ÿ', '¦')
urlcode = ('%25', '%23', '%3B', '%20', '%22', '%3C', '%3E', '%3F',
           '%5B', '%5C', '%5D', '%5E', '%60', '%7B', '%7C', '%7D',
           '%E2%82%AC', '%E2%80%9A', '%C6%92', '%E2%80%9E',
           '%E2%80%A6', '%E2%80%A0', '%E2%80%A1', '%CB%86',
           '%E2%80%B0', '%C5%A0', '%E2%80%B9', '%C5%92', '%C5%BD',
           '%E2%80%98', '%E2%80%99', '%E2%80%9C', '%E2%80%9D',
           '%E2%80%A2', '%E2%80%93', '%E2%80%94', '%CB%9C',
           '%E2%84%A2', '%C5%A1', '%E2%80%BA', '%C5%93', '%C5%BE',
           '%C5%B8', '%C2%A1', '%C2%A2', '%C2%A3', '%C2%A5',
           '%7C', '%C2%A7', '%C2%A8', '%C2%A9', '%C2%AA',
           '%C2%AB', '%C2%AC', '%C2%AF', '%C2%AE', '%C2%AF',
           '%C2%B0', '%C2%B1', '%C2%B2', '%C2%B3', '%C2%B4',
           '%C2%B5', '%C2%B6', '%C2%B7', '%C2%B8', '%C2%B9',
           '%C2%BA', '%C2%BB', '%C2%BC', '%C2%BD', '%C2%BE',
           '%C2%BF', '%C3%80', '%C3%81', '%C3%82', '%C3%83',
           '%C3%84', '%C3%85', '%C3%86', '%C3%87', '%C3%88',
           '%C3%89', '%C3%8A', '%C3%8B', '%C3%8C', '%C3%8D',
           '%C3%8E', '%C3%8F', '%C3%90', '%C3%91', '%C3%92',
           '%C3%93', '%C3%94', '%C3%95', '%C3%96', '%C3%98',
           '%C3%99', '%C3%9A', '%C3%9B', '%C3%9C', '%C3%9D',
           '%C3%9E', '%C3%9F', '%C3%A0', '%C3%A1', '%C3%A2',
           '%C3%A3', '%C3%A4', '%C3%A5', '%C3%A6', '%C3%A7',
           '%C3%A8', '%C3%A9', '%C3%AA', '%C3%AB', '%C3%AC',
           '%C3%AD', '%C3%AE', '%C3%AF', '%C3%B0', '%C3%B1',
           '%C3%B2', '%C3%B3', '%C3%B4', '%C3%B5', '%C3%B6',
           '%C3%B7', '%C3%B8', '%C3%B9', '%C3%BA', '%C3%BB',
           '%C3%BC', '%C3%BD', '%C3%BE', '%C3%BF', '%C2%A6')

rbdb_rep = ('%28', '%29', '%2B', '%27', '%2C', '%3A', '%21',
            '%24', '%26', '%2A', '%2C', '%2D', '%2E', '%3D',
            '%40', '%5F', '%7E')
rbdb_itm = ('(', ')', '+', "'", ',', ':', '!', '$', '&', '*',
            ',', '-', '.', '=', '@', '_', '~')


try:
    cnx = mysql.connector.connect(user=dbuser, password=dbpass,
                                  host=dbhost, database=dbname,
                                  connection_timeout=5)
except mysql.connector.errors.InterfaceError:
    try:
        cnx = mysql.connector.connection.MySQLConnection(user=dbuser,
                                                         password=dbpass,
                                                         host=dbhost,
                                                         database=dbname,
                                                         connection_timeout=5)
    except mysql.connector.errors.InterfaceError:
        pass
#
# Try to get through with ssh fowarding
#
# eg. ssh -L 3306:externalhost:3306 externalhost
#
if not cnx:
    try:
        cnx = mysql.connector.connect(user=dbuser, password=dbpass,
                                      host='localhost', database=dbname, connection_timeout=5)
    except mysql.connector.errors.InterfaceError:
        pass
if cnx:
    print('Connection Established\n')
    playcursor = cnx.cursor()
    executionlist = []
    # total count of plays
    playquery = ('SELECT DISTINCT song.title, artist.name, album.name, ' +
                 'CASE WHEN song.mbid IS NULL THEN \'\' ELSE song.mbid END as smbid, ' +
                 'CASE WHEN artist.mbid IS NULL THEN \'\' ELSE artist.mbid END as ambid, ' +
                 'CASE WHEN album.mbid IS NULL THEN \'\' ELSE album.mbid END as almbid, ' +
                 'COUNT(object_count.object_id), ' +
                 'song.file ' +
                 'FROM object_count ' +
                 'INNER JOIN song on song.id = object_count.object_id AND object_count.object_type = \'song\' ' +
                 'LEFT JOIN artist on artist.id = song.artist ' +
                 'LEFT JOIN album on album.id = song.album ' +
                 'WHERE object_count.object_type = \'song\' ' +
                 'GROUP BY song.title, artist.name, album.name, smbid, ambid, almbid;')
    try:
        playcursor.execute(playquery)
        PROCESSPLAYS = True
    except mysql.connector.errors.ProgrammingError:
        print('ERROR WITH QUERY:\n' + playquery)


# Replace Characters with UTF code value
def set_url(string):
    """ Set RhythmDB style string """
    count = 0
    while count < len(urlascii):
        if urlascii[count] in string:
            while urlascii[count] in string:
                string = string.replace(urlascii[count], urlcode[count])
        count = count + 1
    return string


# Replace UTF Characters with ascii equivilant
def set_asciifull(string):
    """ Set regular path style string """
    count = 0
    string = urllib.parse.unquote(string)
    while count < len(urlascii):
        string = string.replace(urlcode[count], urlascii[count])
        count = count + 1
    return string


def set_ascii(string):
    """ Change unicode codes back to asscii for RhythmDB """
    count = 0
    while count < len(rbdb_rep):
        string = string.replace(rbdb_rep[count],
                                rbdb_itm[count])
        count = count + 1
    return string


# only start if the database has been backed up.
if PROCESSPLAYS or PROCESSLOVED:
    try:
        print('creating rhythmdb backup\n')
        shutil.copy(DB, DBBACKUP)
        DBBACKUP = True
    except FileNotFoundError:
        DBBACKUP = False
    except PermissionError:
        DBBACKUP = False


# only process id db found and backup created.
if os.path.isfile(DB) and DBBACKUP:
    print('Connection Established\n')
    # search for plays by artist, track AND album
    # open the database
    print('Opening rhythmdb for play counts...\n')
    root = etree.parse(os.path.expanduser(DB)).getroot()
    items = [s for s in root.getiterator("entry")
             if s.attrib.get('type') == 'song']
    if items and cnx:
        RBCACHE = []
        RBFILECACHE = []
        print('Building song data for play counts...\n')
        for entries in items:
            if entries.attrib.get('type') == 'song':
                data = {}
                filedata = {}
                for info in entries:
                    if info.tag in ('title', 'artist', 'album', 'mb-trackid', 'mb-artistid', 'mb-albumid'):
                        data[info.tag] = set_asciifull(info.text.lower())
                    if info.tag in 'location':
                        filedata[info.tag] = set_asciifull(info.text).lower().replace('file://', '')
            try:
                RBCACHE.append('%(title)s\t%(artist)s\t%(album)s\t%(mb-trackid)s' +
                               '\t%(mb-artistid)s\t%(mb-albumid)s' % data)
            except KeyError:
                RBCACHE.append('%(title)s\t%(artist)s\t%(album)s\t\t\t' % data)
            RBFILECACHE.append('%(location)s' % filedata)
        WEHAVEMERGED = True
        print('Processing mysql play counts\n')
        if playcursor:
            changemade = False
            for row in playcursor:
                tmprow = []
                tmpsong = None
                tmpartist = None
                tmpalbum = None
                tmpentry = None
                mergeplays = False
                foundartist = None
                foundalbum = None
                foundsong = None
                idx = None
                tmpcheck = None
                tmpfilecheck = None
                # using the last.fm data check for the same song in rhythmbox
                try:
                    test = row[0]
                except IndexError:
                    test = None
                if test:
                    if not mergeplays:
                        # Check for a match using the id3 tags
                        tmpcheck = (str(row[0].lower()) + '\t' + str(row[1].lower()) + '\t' +
                                    str(row[2].lower()) + '\t' + str(row[3]).replace('None', '') + '\t' +
                                    str(row[4]).replace('None', '') + '\t' + str(row[5]).replace('None', ''))
                        if tmpcheck in RBCACHE:
                            idx = RBCACHE.index(tmpcheck)
                    if not idx:
                        # When you can't match tags, check filename
                        if FIND and REPLACE:
                            tmpfilecheck = str(row[7].lower()).replace(FIND, REPLACE)
                        else:
                            tmpfilecheck = str(row[7].lower())
                        if tmpfilecheck in RBFILECACHE:
                            idx = RBFILECACHE.index(tmpfilecheck)
                # if the index is found, update the playcount
                if idx:
                    entry = items[idx]
                    tmpplay = '0'
                    for info in entry:
                        if info.tag == 'play-count':
                            tmpplay = str(info.text)
                            if str(info.text) == str(row[6]):
                                mergeplays = True
                            elif not str(info.text) == str(row[6]):
                                changemade = True
                                print('Updating playcount for', row[0], 'from ' + tmpplay + ' to', row[6])
                                info.text = str(row[6])
                                mergeplays = True
                    if not mergeplays:
                        changemade = True
                        print('Inserting playcount for', row[0], 'as', row[6])
                        insertplaycount = etree.SubElement(entry, 'play-count')
                        insertplaycount.text = str(row[6])
                        mergeplays = True
                # if not mergeplays:
                #    print('entry not found')
                #    #print(row)
                #    print(tmpcheck)
            if changemade:
                print('Plays from mysql have been inserted into the database.\n')
                # Save changes
                print('saving changes')
                output = etree.ElementTree(root)
                output.write(os.path.expanduser(DB), encoding="utf-8")
            else:
                print('No play counts changed')
    else:
        print('no play data found\n')
else:
    # there was a problem with the command
    print('FILE NOT FOUND.\nUnable to process\n')


if cnx:
    print('Connection Established\n')
    ratingcursor = cnx.cursor(buffered=True)
    executionlist = []
    # ampache ratings for all songs
    ratingquery = ('SELECT DISTINCT song.title, artist.name, album.name, ' +
                   'CASE WHEN song.mbid IS NULL THEN \'\' ELSE song.mbid END as smbid, ' +
                   'CASE WHEN artist.mbid IS NULL THEN \'\' ELSE artist.mbid END as ambid, ' +
                   'CASE WHEN album.mbid IS NULL THEN \'\' ELSE album.mbid END as almbid, ' +
                   'rating.rating, ' +
                   'song.file ' +
                   'FROM rating ' +
                   'INNER JOIN song on song.id = rating.object_id AND rating.object_type = \'song\' ' +
                   'LEFT JOIN artist on artist.id = song.artist ' +
                   'LEFT JOIN album on album.id = song.album ' +
                   'WHERE rating.object_type = \'song\' AND ' +
                   'rating.user = ' + str(myid))
    try:
        ratingcursor.execute(ratingquery)
        PROCESSLOVED = True
    except mysql.connector.errors.ProgrammingError as e:
        print('ERROR WITH QUERY:\n' + ratingquery)
        print(e)

    if PROCESSLOVED and ratingcursor and DBBACKUP:
        print('Opening rhythmdb...\n')
        root = etree.parse(os.path.expanduser(DB)).getroot()
        items = [s for s in root.getiterator("entry")
                 if s.attrib.get('type') == 'song']
        RBCACHE = []
        RBFILECACHE = []
        print('Building song data for ratings...\n')
        for entries in items:
            if entries.attrib.get('type') == 'song':
                data = {}
                filedata = {}
                for info in entries:
                    if info.tag in ('title', 'artist', 'album', 'mb-trackid', 'mb-artistid', 'mb-albumid'):
                        data[info.tag] = set_asciifull(info.text.lower())
                    if info.tag in 'location':
                        filedata[info.tag] = set_asciifull(info.text).lower().replace('file://', '')
            try:
                RBCACHE.append('%(title)s\t%(artist)s\t%(album)s\t%(mb-trackid)s' +
                               '\t%(mb-artistid)s\t%(mb-albumid)s' % data)
            except KeyError:
                RBCACHE.append('%(title)s\t%(artist)s\t%(album)s\t\t\t' % data)
            RBFILECACHE.append('%(location)s' % filedata)
        WEHAVEMERGED = True
        print('Processing mysql track ratings\n')
        if ratingcursor:
            changemade = False
            for row in ratingcursor:
                tmprow = []
                tmpsong = None
                tmpartist = None
                tmpalbum = None
                tmpentry = None
                mergeplays = False
                foundartist = None
                foundalbum = None
                foundsong = None
                idx = None
                tmpcheck = None
                tmpfilecheck = None
                # using the last.fm data check for the same song in rhythmbox
                try:
                    test = row[0]
                except IndexError:
                    test = None
                if test:
                    if not mergeplays:
                        # Check for a match using the id3 tags
                        tmpcheck = (str(row[0].lower()) + '\t' + str(row[1].lower()) + '\t' +
                                    str(row[2].lower()) + '\t' + str(row[3]).replace('None', '') + '\t' +
                                    str(row[4]).replace('None', '') + '\t' + str(row[5]).replace('None', ''))
                        if tmpcheck in RBCACHE:
                            idx = RBCACHE.index(tmpcheck)
                    if not idx:
                        # When you can't match tags, check filename
                        if FIND and REPLACE:
                            tmpfilecheck = str(row[7].lower()).replace(FIND, REPLACE)
                        else:
                            tmpfilecheck = str(row[7].lower())
                        if tmpfilecheck in RBFILECACHE:
                            idx = RBFILECACHE.index(tmpfilecheck)
                # if the index is found, update the playcount
                if idx:
                    # print(idx)
                    entry = items[idx]
                    for info in entry:
                        if info.tag == 'rating':
                            if str(info.text) == str(row[6]):
                                mergeplays = True
                            elif not str(info.text) == str(row[6]):
                                changemade = True
                                info.text = str(row[6])
                                mergeplays = True
                    if not mergeplays:
                        changemade = True
                        print('Inserting rating for', row[0], 'as', row[6])
                        insertplaycount = etree.SubElement(entry, 'rating')
                        insertplaycount.text = str(row[6])
                        mergeplays = True
                # if not mergeplays:
                #    print('entry not found')
                #    #print(row)
                #    print(tmpcheck)
            if changemade:
                print('Ratings from mysql have been rated in the database.\n')
                # Save changes
                print('saving changes')
                output = etree.ElementTree(root)
                output.write(os.path.expanduser(DB), encoding="utf-8")
            else:
                print('No Ratings were updated.')
    else:
        print('no rating data found\n')
else:
    # there was a problem with the command
    print('FILE NOT FOUND.\nUnable to process\n')

print('Done\n')
