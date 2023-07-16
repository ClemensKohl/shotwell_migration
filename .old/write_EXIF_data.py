#!/usr/bin/python

# An example of how to query the shotwell database with pandas
import sqlite3, pandas, os, time, datetime

con = sqlite3.connect('/home/dov/.local/share/shotwell/data/photo.db')
photo_df = pandas.read_sql("SELECT * from PhotoTable", con)

for c in ['exposure_time','timestamp','time_created']:
  photo_df[c] = photo_df[c].map(datetime.datetime.fromtimestamp)

tag_df = pandas.read_sql('SELECT * from TagTable', con)

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
ids1 = get_image_ids('cat')
ids2 = get_image_ids('sleeping')
rows = get_photos(ids1.intersection(ids2))

# An example of how to filter the rows by timestamp
time_low,time_high = datetime.datetime(2006,8,1),datetime.datetime(2009,1,1)
rows = rows[(rows.exposure_time > time_low)
            & (rows.exposure_time < time_high)]
print '\n'.join([str(ts) for ts in rows['exposure_time']])
view_pix(rows)

print 'done'