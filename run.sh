
set -euo pipefail

docker build . -t budget_helper

tmp_in=$(mktemp -d input.XXXX)
host_in_dir=$PWD/$tmp_in
host_out_dir=$PWD/output
mkdir -p $host_in_dir
mkdir -p $host_out_dir
cp $CAT_FILE $host_in_dir/.
container_in_files=()
IFS_BAK="$IFS"
IFS=$'\n'
for file in $(find "${IN_FOLDER}" -iname "*.csv"); do
  cp "$file" $host_in_dir/.
  container_in_files+=(input/$(basename "$file"))
done
IFS="$IFS_BAK"

echo "CAT_FILE: $CAT_FILE"
echo "IN_FILES: ${container_in_files[@]}"

docker run --rm -it\
  -e LOG_LEVEL=${LOG_LEVEL:='INFO'}\
  --mount type=bind,src=$host_in_dir,dst=/usr/src/app/input,ro=true\
  --mount type=bind,src=$host_out_dir,dst=/usr/src/app/output,ro=false\
  budget_helper\
  python ./src/budget_helper_bhass1/main.py\
    input/$(basename $CAT_FILE)\
    "${container_in_files[@]}"\
    output/out.xlsx

rm -r $host_in_dir
