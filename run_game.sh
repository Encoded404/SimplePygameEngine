#!/bin/bash

# find all folders starting with _
for dir in _*/ ; do
    # remove the leading underscore and trailing slash to get the game name, then add it to the array
    game_names+=("${dir:1:-1}")
done

# if a number is passed as an argument, use that as the game index
if [[ -n "$1" && "$1" =~ ^[0-9]+$ && "$1" -ge 0 && "$1" -lt "${#game_names[@]}" ]]; then
    game_index="$1"
else
    for i in "${!game_names[@]}"; do
        echo "${i}: ${game_names[i]}"
    done

    # get what game to run
    read -p "Enter the number of the game to run: " game_index
fi

# run the selected game
if [[ -n "${game_names[game_index]}" ]]; then
    echo "Running game: ${game_names[game_index]}"
else
    echo "Invalid game selection."
    exit
fi

mkdir -p temp

cp -r _${game_names[game_index]}/* temp/
cp -r engine/ temp/
cp -r .venv/ temp/

cd temp

python3 game.py

cd ..

rm -r temp