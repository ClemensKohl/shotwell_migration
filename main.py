#!/usr/bin/python

# Query Shotwell database and write ratings and tags to EXIF data.

import sqlite3, pandas, os, time, datetime
import numpy as np
import subprocess

con = sqlite3.connect('/home/clemens/.local/share/shotwell/data/photo_backup.db')
photo_df = pandas.read_sql("SELECT * from PhotoTable", con)

for c in ['exposure_time','timestamp','time_created']:
  photo_df[c] = photo_df[c].map(datetime.datetime.fromtimestamp)

tag_df = pandas.read_sql('SELECT * from TagTable', con)

def flatten(l):
    """ Flatten a list of lists """
    return [item for sublist in l for item in sublist]

def swap_keys(old_dict):
    """ Swaps the keys and values in a dict """

    new_dict = {}
    for key, values in old_dict.items():
        for item in values:
            if item in new_dict: # values can be duplicates!
                new_dict[item].append(key)
            else:
                new_dict[item] = [key]
    return new_dict


def get_all_tagged_ids(tag_df):
    """get the ids of all tagged photos
      The image ids are stored morphed in the database as %016x integers.
      """

    tag_ids = {}
    # iterate over tags
    for i, row in tag_df.iterrows():
        photo_ids = []
        # iterate over split ids (the photos)
        for s in row.photo_id_list.split(','):

            # we don't care about videos
            if "video" in s:
                continue

            s = s.replace('thumb', '')
            #convert to id
            if len(s):
                photo_ids.append(int(s, 16))

        tag_ids[row["name"]] = list(set(photo_ids))

    return tag_ids

def get_all_rated_ids(photo_df):
    r_ids = {} # rating by photo
    # photo_ids = []

    # iterate over ratings
    for i, row in photo_df.iterrows():
        if row.rating != 0:
            r_ids[row.id] = row.rating

    return r_ids

def subset_to_changed(df, ids, ):
    """Only keep tagged and/or pictures with a rating."""

    rated = np.array([df["rating"] != 0])
    tagged = np.array([df.id.isin(ids)])

    photo_tr = df.loc[(rated | tagged).reshape(-1), :]

    return(photo_tr)

def add_tags_to_df(df, tags_by_id):
    """ Add the tags to the data frame"""
    df.loc[:, ("tags")] = np.nan

    for photo, tags in tags_by_id.items():
        df.loc[df.id.isin([photo]), ("tags") ] = ",".join(tags)

    return df

def get_commands(photo_df, tag_df):

    """
    make a list of commands to write to EXIF data
    using exiftools
    """

    rated_photos = get_all_rated_ids(photo_df)
    tagged_photos = get_all_tagged_ids(tag_df)
    tagged_photos = swap_keys(tagged_photos)

    commands = []

    for id, rating in rated_photos.items():
        photo = photo_df.filename[photo_df.id == id].item()
        commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=rating%d \"%s\"" % (rating, photo))

    for id, tag in tagged_photos.items():

        photo = photo_df.filename[photo_df.id == id].item()
        # for t in tag:
        commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=%s \"%s\"" % (tag, photo))

    return commands


def extract_exif(file):
    """ Extract exif data of a file as a data frame"""
    infoDict = {}  # Creating the dict to get the metadata tags
    exifToolPath = "exiftool"

    # use Exif tool to get the metadata
    process = subprocess.Popen([exifToolPath, file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True)

    # get the tags in dict
    for tag in process.stdout:
        line = tag.strip().split(':')
        infoDict[line[0].strip()] = line[-1].strip()

    return infoDict

def print_exif(infoDict):
    """ Just print me the exif data so I can read it god damnit """
    for k, v in infoDict.items():
        print(k, ':', v)

# Generate data frames
ids_by_tag = get_all_tagged_ids(tag_df)
tags_by_id = swap_keys(ids_by_tag)

# bit of filtering
unique_ids = list(set(
                flatten(ids_by_tag.values())
                ))

# retrospectively, this is not really necessary.
# kept because possibly I want to write it out as some kind of log file.
photo_tr = subset_to_changed(photo_df, unique_ids)
photo_tr_tagged = add_tags_to_df(photo_tr,  tags_by_id)

# get tagging/rating commands
cmds = get_commands(photo_tr_tagged, tag_df)

# TODO: make a safety copy of each file edited to a folder keeping the original dir structure.
# TODO: check if rating is already in file. If yes, what then?!

