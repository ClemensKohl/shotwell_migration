#!/bin/bash

rename_files() {
  local dir=$1
  local year month day
  # local file_extension="_ARW_embedded.jpg"
  local dupl_extension="_ARW_embedded*.jpg"
  local shotwell_extension="_ARW_shotwell*.jpg"
  local new_extension=".jpg"

  local arw_dupl_extention="_1.ARW"
  local arw_extention=".ARW"

  # Iterate over directories
  for year in "$dir"/20*; do
    if [[ -d "$year" ]]; then
      for month in "$year"/*; do
        if [[ -d "$month" ]]; then
          # Check if the month directory name consists of 2 digits
          if [[ $(basename "$month") =~ ^[0-9]{2}$ ]]; then
            for day in "$month"/*; do
              if [[ -d "$day" ]]; then
                # Check if the day directory name consists of 2 digits
                if [[ $(basename "$day") =~ ^[0-9]{2}$ ]]; then
                  # Rename files in the current day directory
                  # for file in "$day"/*"$file_extension"; do
                  #   if [[ -f "$file" ]]; then

                  #     local new_name="${file%$file_extension}$new_extension"
                  #     mv "$file" "$new_name"
                  #     echo "Renamed $file to $new_name"
                     
                  #   fi
                  # done


                  for file in "$day"/*$arw_dupl_extention; do
                    if [[ -f "$file" ]]; then
                      # Move duplicate files to duplicates directory preserving directory structure
                      local relative_path="${file#$dir}"
                      local filename=$(basename "$file")
                      local duplicate_dir="$dir/duplicates${relative_path%$filename}"
                      local duplicate_file="$duplicate_dir/${file##*/}"

                      local new_name="${file%$arw_dupl_extention}$arw_extention"
                        if [[ ! -f "$new_name" ]]; then
                          mv "$file" "$new_name"
                          echo "Renamed $file to $new_name because no $arw_extention was present."
                        else
                        
                          mkdir -p "$duplicate_dir"
                          mv "$file" "$duplicate_file"
                          echo "Moved $file to $duplicate_file"
                      fi
                    fi
                  done


                  for file in "$day"/*$dupl_extension; do
                    if [[ -f "$file" ]]; then
                      # Move duplicate files to duplicates directory preserving directory structure
                      local relative_path="${file#$dir}"
                      local filename=$(basename "$file")
                      local duplicate_dir="$dir/duplicates${relative_path%$filename}"
                      local duplicate_file="$duplicate_dir/${file##*/}"

                      # local new_name="${file%$dupl_extension}$new_extension"
                      #   if [[ ! -f "$new_name" ]]; then
                      #     mv "$file" "$new_name"
                      #     echo "Renamed $file to $new_name because no $file_extension was present."
                      #   else
                        
                          mkdir -p "$duplicate_dir"
                          mv "$file" "$duplicate_file"
                          echo "Moved $file to $duplicate_file"
                      # fi
                    fi
                  done

                  for file in "$day"/*$shotwell_extension; do
                    if [[ -f "$file" ]]; then
                      # Move duplicate files to duplicates directory preserving directory structure
                      local relative_path="${file#$dir}"
                      local filename=$(basename "$file")
                      local duplicate_dir="$dir/duplicates${relative_path%$filename}"
                      local duplicate_file="$duplicate_dir/${file##*/}"


                      mkdir -p "$duplicate_dir"
                      mv "$file" "$duplicate_file"
                      echo "Moved $file to $duplicate_file"
                    fi
                  done

                fi
              fi
            done
          fi
        fi
      done
    fi
  done
}

# Run the script by passing the root directory as an argument
if [[ -z $1 ]]; then
  echo "Please provide the root directory as an argument."
  exit 1
fi

root_dir="$1"
rename_files "$root_dir"

