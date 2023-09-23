# shotwell_migration
Scripts to write tags and ratings to the image files for easier migration from Shotwell to digikam.

The `delete_shotwell_duplicates.sh` script will go through folders (you need to set the structure) and delete shotwell duplicates it generates from RAW files.
Currently the script assumes a year/month/day folder structure. If you do not use that it might be unusable.

`main.py` takes as input a shotwell database and writes all the exiftool commands that need to be applied to write the tags and ratings to the image files into a new file.
It _does not_ write to RAW files, but instead writes to a .xmp sidecar file.

These scripts are very crude and not very well organized but did the job for me. Feel free to use them if they help you or let me know if you need help using them.
Many pathes are obv. the ones of the files on my hard drive. They will need to be changed.

