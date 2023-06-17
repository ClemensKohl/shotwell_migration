import os
conn = sqlite3.connect("/home/  username  /.shotwell/data/photo.db")

def get_tags():
    return [ x[0] for x in conn.execute("SELECT name FROM TagTable").fetchall()]

def tag_query(tag):
    return conn.execute("SELECT photo_id_list FROM TagTable WHERE name=?", (tag,)).fetchone()[0].split(",")

def get_tagged_photos(tag):
    for id in tag_query(tag):
        result = conn.execute("select filename from PhotoTable where id=?", (id,) ).fetchone()
        if result:
            yield result[0]

def get_photos_by_rating(rating):
    return [photo[0] for photo in conn.execute("select filename from PhotoTable where rating=?",(rating,)).fetchall()]

def get_tagging_commands():
    commands = []
    for rating in range(1,5):
        for photo in get_photos_by_rating(rating):
             commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=rating%d \"%s\""% (rating,photo))

    for tag in [tag for tag in get_tags() if tag != "keep"]:
        for photo in get_tagged_photos(tag):
             commands.append("exiftool -overwrite_original_in_place -preserve -keywords+=%s \"%s\"" % (tag,photo))

    return commands

commands = get_tagging_commands()
for command in commands:
    print command
    os.system(command)