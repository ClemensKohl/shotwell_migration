#!/usr/bin/python

# Query Shotwell database and write ratings and tags to EXIF data.

import sqlite3, pandas, os, time, datetime
import numpy as np
import subprocess

con = sqlite3.connect('/home/clemens/.local/share/shotwell/data/photo.db')
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
        if row.photo_id_list is None: continue

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

def get_ext(file):
    file_name, file_extension = os.path.splitext(file)
    return file_extension

def get_filename(file):
    file_name, file_ext = os.path.splitext(file)
    return file_name


def find_jpgs(file):
    name = get_filename(file)

    jpgs = [name + z for z in [".jpg", ".jpeg", ".JPG", ".JPEG"]]
    jpgs = [j for j in jpgs if os.path.isfile(j)]

    return jpgs


def find_RAWs(file):
    name = get_filename(file)

    raws = [name + z for z in [".RAF", ".ARW"]]
    raws = [r for r in raws if os.path.isfile(r)]

    return raws

def get_commands(photo_df, tag_df, cp_target):

    """
    make a list of commands to write to EXIF data
    using exiftools
    """

    rated_photos = get_all_rated_ids(photo_df)
    tagged_photos = get_all_tagged_ids(tag_df)
    tagged_photos = swap_keys(tagged_photos)

    cp_commands = []
    commands = []
    xmp_commands = []
    nonexist = []


    # digikam seems to recognize the following format (*.RAF.xmp):
    # exiftool /media/clemens/Foto1/Pictures/2023/04/21/_DSF0948.RAF -o /media/clemens/Foto1/Pictures/2023/04/21/_DSF0948.RAF.xmp "-all:all<xmp:all"
    # the xmp file can be edited just like a RAW/jpg file:
    # exiftool -overwrite_original_in_place -preserve  -xmp:TagsList+='xmptag' /media/clemens/Foto1/Pictures/2023/05/29/DSCF1714.RAF.xmp
    # so defacto you just first check if its a RAF file, then create xmp sidecar, and concat .xmp to the filename.
    # Checking if there is a JPG should be done independent for ARW and RAF.

    for id, rating in rated_photos.items():

        photo = photo_df.filename[photo_df.id == id].item()
        write_file = photo

        if not os.path.isfile(photo):
            nonexist.append(photo)
            continue

        # WIP: Detect if RAW or JPG.
        ext = get_ext(photo)

        rating_start = "exiftool -overwrite_original_in_place -preserve "
        if ext == ".ARW" or ext == ".RAF":
            xmp = photo + ".xmp"
            xmp_cmd = "exiftool \'{}\' -o \'{}\' '-all:all<xmp:all'".format(photo, xmp)
            xmp_commands.append(xmp_cmd)

            # Write data to xmp file INSTEAD of RAW file.
            write_file = xmp


        # INFO: If you prefer to instead write the information also to the file itself, move the else block to before
        # checking if it is a RAW file, then, we do not need to also write it to the xmp file.

        if rating == -1:
            commands.append(rating_start + "-xmp:PickLabel=1 \'{}\'".format(write_file))
        else:
            commands.append(rating_start + "-xmp:Rating=%d \'%s\'" % (rating, write_file))

        backup_photo = move_photo_to_path(source=photo, target=cp_target, root=None)
        backup_dir = os.path.dirname(backup_photo)
        cp_commands.append("mkdir -p \'{}\' && cp -v \'{}\' \'{}\'".format(backup_dir, photo, backup_photo))


        # For each RAW file check if a jpg exists and write the metadata to it too. (and vice versa)
        if ext == ".ARW" or ext == ".RAF":
            extra_files = find_jpgs(photo)
        elif ext in [".jpg", ".jpeg", ".JPG", ".JPEG"]:
            extra_files = find_RAWs(photo)
        if len(extra_files) != 0:
            for ef in extra_files:

                if ef in set(photo_df["filename"]:
                    efid = photo_df.id[photo_df.filename == ef].item()
                    if efid in rated_photos.keys():
                        continue


                backup_photo = move_photo_to_path(source=ef, target=cp_target, root=None)
                backup_dir = os.path.dirname(backup_photo)
                cp_commands.append("mkdir -p \'{}\' && cp -v \'{}\' \'{}\'".format(backup_dir, photo, backup_photo))

                ext = get_ext(ef)
                if ext == ".ARW" or ext == ".RAF":
                    xmp = photo + ".xmp"
                    xmp_cmd = "exiftool \'{}\' -o \'{}\' '-all:all<xmp:all'".format(ef, xmp)
                    xmp_commands.append(xmp_cmd)
                    ef = xmd

                if rating == -1:
                    commands.append(rating_start + "-xmp:PickLabel=1 \'{}\'".format(ef))
                else:
                    commands.append(rating_start + "-xmp:Rating=%d \'%s\'" % (rating, ef))





    for id, tag in tagged_photos.items():
        # i+=1
        photo = photo_df.filename[photo_df.id == id].item()
        write_file = photo
        # get tags:
        # exif_df = extract_exif(photo)
        # if tag is exif_df["Keywords"]: continue

        if not os.path.isfile(photo):
            nonexist.append(photo)
            continue

        if type(tag) is not list:
            tag = tag.split(', ')

        ext = get_ext(photo)
        if ext == ".ARW" or ext == ".RAF":
            xmp = photo + ".xmp"
            xmp_cmd = "exiftool \'{}\' -o \'{}\' '-all:all<xmp:all'".format(photo, xmp)
            xmp_commands.append(xmp_cmd)
            write_file = xmp


        cmd_start = "exiftool -overwrite_original_in_place -preserve"
        keywords = ""
        # cmd_end = photo
        for t in tag:
            keywords += " -xmp:Subject-=\'{}\' -xmp:Subject+=\'{}\' -xmp:TagsList-=\'{}\' -xmp:TagsList+=\'{}\'".format(t, t, t, t)

        cmd = cmd_start + keywords + " " + "\'" + write_file + "\'"
        commands.append(cmd)
        # commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=%s \"%s\"" % (tag, photo))

        backup_photo = move_photo_to_path(source=photo, target=cp_target, root=None)
        backup_dir = os.path.dirname(backup_photo)
        cp_commands.append("mkdir -p \'{}\' && cp -v \'{}\' \'{}\'".format(backup_dir, photo, backup_photo))

        # For each RAW file check if a jpg exists and write the metadata to it too. (and vice versa)
        if ext == ".ARW" or ext == ".RAF":
            extra_files = find_jpgs(photo)
        elif ext in [".jpg", ".jpeg", ".JPG", ".JPEG"]:
            extra_files = find_RAWs(photo)

        if len(extra_files) != 0:
            for ef in extra_files:

                if ef in set(photo_df["filename"]:
                    efid = photo_df.id[photo_df.filename == ef].item()
                    if efid in tagged_photos.keys():
                        continue

                backup_photo = move_photo_to_path(source=ef, target=cp_target, root=None)
                backup_dir = os.path.dirname(backup_photo)
                cp_commands.append("mkdir -p \'{}\' && cp -v \'{}\' \'{}\'".format(backup_dir, photo, backup_photo))

                ext = get_ext(ef)
                if ext == ".ARW" or ext == ".RAF":
                    xmp = photo + ".xmp"
                    xmp_cmd = "exiftool \'{}\' -o \'{}\' '-all:all<xmp:all'".format(ef, xmp)
                    xmp_commands.append(xmp_cmd)
                    ef = xmd

                cmd = cmd_start + keywords + " " + "\'" + ef + "\'"
                commands.append(cmd)



    cp_commands = set(cp_commands)

    return cp_commands, commands, nonexist


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


def move_photo_to_path(source, target, root=None):
    """
    Take a given photo file and copy it into the target folder,
     while maintaining its relative path based on the root picture folder.
    :param source:
    :param target:
    :param root:
    :return:
    """

    if root is None:
        root = os.path.commonpath([source, target])
        rel_path_target = os.path.relpath(target, root)

    else:
        rel_path_target = os.path.basename(target)


    rel_path_source = os.path.relpath(source, root)

    cp_path = os.path.join(root, rel_path_target, rel_path_source)

    return cp_path

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
cp_cmds, exif_cmds, nonexist = get_commands(photo_tr_tagged, tag_df, cp_target = "/media/clemens/Foto1/Pictures/backups")

# os.makedirs("./out", exist_ok=True)
#
# cp_file=open('./out/cp_cmds.sh','w')
#
# cp_file.write('#!/bin/bash')
# cp_file.write('\n')
# for c in cp_cmds:
#      cp_file.write(c)
#      cp_file.write('\n')
#      # cp_file.write("echo \"{}\"".format(c))
#      # cp_file.write('\n')
# cp_file.close()
#
# exif_file=open('./out/exif_cmds.sh','w')
#
# exif_file.write('#!/bin/bash')
# exif_file.write('\n')
#
# for e in exif_cmds:
#      exif_file.write("echo \"{}\"".format(e))
#      exif_file.write('\n')
#      exif_file.write(e)
#      exif_file.write('\n')
#
# exif_file.close()
#
# nonexist_file=open('./out/nonexist.txt','w')
# for f in nonexist:
#      nonexist_file.write(f)
#      nonexist_file.write('\n')
#
# nonexist_file.close()

# # create backups:
# for cp in cp_cmds:
#     print(cp)
#     os.system(cp)
#
# # write exif data.
# for ecmd in exif_cmds:
#     print(ecmd)
#     os.system(ecmd)
