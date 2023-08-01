
mkdir -p ./out/logs

today=$(date +'%Y%m%d')

bash ./chatgpt_mv.sh /media/clemens/Foto1/Pictures/ &> ./out/logs/${today}_chatgpt_mv.log
python3 ./main.py &> ./out/logs/${today}_main.log

bash ./out/cp_cmds.sh &> ./out/logs/${today}_backup_copy.log
bash ./out/xmp_cmds.sh &> ./out/logs/${today}_xmp.log
bash ./out/exif_cmds.sh &> ./out/logs/${today}_exif.log

