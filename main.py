#!/usr/bin/python

# An example of how to query the shotwell database with pandas
import sqlite3, pandas, os, time, datetime
import numpy as np

con = sqlite3.connect('/home/clemens/.local/share/shotwell/data/photo_backup.db')
photo_df = pandas.read_sql("SELECT * from PhotoTable", con)

for c in ['exposure_time','timestamp','time_created']:
  photo_df[c] = photo_df[c].map(datetime.datetime.fromtimestamp)

tag_df = pandas.read_sql('SELECT * from TagTable', con)

def flatten(l):
    return [item for sublist in l for item in sublist]

def swap_keys(old_dict):
    new_dict = {}
    for key, values in old_dict.items():
        for item in values:
            if item in new_dict:
                new_dict[item].append(key)
            else:
                new_dict[item] = [key]
    return new_dict


def get_all_tagged_ids(tag_df):
    """get the ids of all tagged photos
      The image ids are stored morphed in the database as %016x
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



def subset_to_changed(df, ids, ):
    """Only keep tagged and/or pictures with a rating."""

    rated = np.array([df["rating"] != 0])
    tagged = np.array([df.id.isin(ids)])

    photo_tr = df.loc[(rated | tagged).reshape(-1), :]

    return(photo_tr)

def add_tags_to_df(df, tags_by_id):

    df.loc[:, ("tags")] = np.nan

    for photo, tags in tags_by_id.items():
        df.loc[df.id.isin([photo]), ("tags") ] = ",".join(tags)

    return df


def get_tagging_commands():
    commands = []
    for rating in range(1,5):
        for photo in get_photos_by_rating(rating):
             commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=rating%d \"%s\""% (rating,photo))

    for tag in [tag for tag in get_tags() if tag != "keep"]:
        for photo in get_tagged_photos(tag):
             commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=%s \"%s\"" % (tag,photo))

    return commands



# Generate data frames
ids_by_tag = get_all_tagged_ids(tag_df)
tags_by_id = swap_keys(ids_by_tag)

unique_ids = list(set(
                flatten(ids_by_tag.values())
                ))

photo_tr = subset_to_changed(photo_df, unique_ids)
photo_tr_tagged = add_tags_to_df(photo_tr,  tags_by_id)





###########################

def get_image_ids(tag):
  """The image ids are stored morphed in the database as %016x"""
  global tag_df

  return set([int(s.replace('thumb',''),16)
              for s in tag_df[tag_df.name==tag].photo_id_list.iloc[0].split(',')
              if len(s)])

def get_photos(ids):
  """Get the photos for a list of ids"""
  global photo_df
  return photo_df[photo_df.id.isin(ids)].sort(['exposure_time'])

def view_pix(rows):
  cmd = ('eog ' + ' '.join(['"%s"'%row.filename
                            for idx,row in rows.iterrows()]))
#  print cmd
  os.system(cmd)

print 'querying...'

# An example of how to create an intersection of two tags
ids1 = get_image_ids('shirkan')
ids2 = get_image_ids('sleeping')
rows = get_photos(ids1.intersection(ids2))

# An example of how to filter the rows by timestamp
time_low,time_high = datetime.datetime(2006,8,1),datetime.datetime(2009,1,1)
rows = rows[(rows.exposure_time > time_low)
            & (rows.exposure_time < time_high)]
print '\n'.join([str(ts) for ts in rows['exposure_time']])
view_pix(rows)

print 'done'