import os
from PIL import Image
import hashlib

import json

def handleWrongBackgroundInfo(old_background_info, background_info, currentLevel):
    # Placeholder for handling discrepancies between old and new background info

    print("background info changed, updating background " + str(currentLevel))
    print("old info: " + str(old_background_info))
    print("new info: " + str(background_info))
    # delete the old background files
    if(old_background_info != None):
        for y in range(old_background_info["num_chunks"][1]):
            for x in range(old_background_info["num_chunks"][0]):
                old_file = os.path.join(os.path.dirname(__file__), 'backgrounds', f"{currentLevel}_{x - (old_background_info['num_chunks'][0] // 2)}_{y - (old_background_info['num_chunks'][1] // 2)}.png")
                if os.path.exists(old_file):
                    os.remove(old_file)
    else:
        print("No old background info to delete files from. using general cleanup")
        # remove all backgrounds named "currentLevel_*.png"
        backgrounds_dir = os.path.join(os.path.dirname(__file__), 'backgrounds')
        if not os.path.exists(backgrounds_dir):
            os.makedirs(backgrounds_dir, exist_ok=True)

        for filename in os.listdir(backgrounds_dir):
            if filename.startswith(f"{currentLevel}_") and filename.endswith(".png"):
                file_path = os.path.join(backgrounds_dir, filename)
                os.remove(file_path)

class BackgroundCreator:
    def createBackgrounds(self, path: str, currentLevel, section_size=(30, 20)):
        # 1. Load or create an image
        img = Image.open(path)  # or create a new image
        # img = Image.new("RGB", (300, 200), color="white")  # example of creating a blank image

        # 2. Resize to low resolution (optional)
        #low_res = img.resize((300, 200), Image.NEAREST)  # change size as needed

        # 3. Split into 30x20 pixel chunks
        chunk_width = section_size[0]  # 30
        chunk_height = section_size[1]  # 20

        # Number of chunks in x and y
        num_chunks_x = img.width // chunk_width
        num_chunks_y = img.height // chunk_height

        center_x = num_chunks_x // 2
        center_y = num_chunks_y // 2

        # save all information regarding this background
        background_info = {
            # general info
            "level": currentLevel,
            "chunk_size": list(section_size),
            "num_chunks": [num_chunks_x, num_chunks_y],

            # image hash
            "image_hash": hashlib.md5(img.tobytes()).hexdigest(),
            # date changed
            "date_changed": os.path.getmtime(path)
        }

        # get old background info if it exists
        old_background_info = None
        info_path = os.path.join(os.path.dirname(__file__), 'backgrounds', f"{currentLevel}.json")
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                old_background_info = json.load(f)
                if(old_background_info != None and background_info == old_background_info):
                    print(f"background {currentLevel} info unchanged, skipping background creation")
                    return (num_chunks_x, num_chunks_y)
                else:
                    handleWrongBackgroundInfo(old_background_info, background_info, currentLevel)
        else:
            print(f"no existing background info, creating new background {currentLevel}")
            handleWrongBackgroundInfo(old_background_info, background_info, currentLevel)

        
        # Save new background info
        with open(info_path, 'w') as f:
            json.dump(background_info, f)

        for y in range(num_chunks_y):
            for x in range(num_chunks_x):
                box = (x*chunk_width, y*chunk_height, (x+1)*chunk_width, (y+1)*chunk_height)
                chunk = img.crop(box)
                # File name relative to center
                filename = f"{os.path.dirname(__file__)+os.sep}backgrounds{os.sep}{currentLevel}_{x - center_x}_{y - center_y}.png"
                
                # Ensure the directory exists before saving
                dir_path = os.path.dirname(filename)
                if not os.path.exists(dir_path):
                    print("internal backgrounds folder doesnt exist yet, creating")
                    os.makedirs(dir_path, exist_ok=True)

                # Save the chunk, overwriting any existing file
                chunk.save(filename, "PNG")

        return (num_chunks_x, num_chunks_y)