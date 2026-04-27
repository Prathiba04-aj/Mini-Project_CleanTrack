import os
import shutil
import random
import uuid

# --- CONFIGURATION ---
BASE_DIR = "dataset"

if os.path.exists("temp_datasets"):
    TEMP_DIR = "temp_datasets"
elif os.path.exists(os.path.join("dataset", "temp_datasets")):
    TEMP_DIR = os.path.join("dataset", "temp_datasets")
else:
    TEMP_DIR = "temp_datasets"

SPLITS = {"train": 0.8, "validation": 0.1, "test": 0.1}

# Specific materials we want to track
CATEGORIES = [
    "plastic", "metal", "paper", "glass", "cardboard", "battery", "biological", "trash"
]

def setup_directories(found_categories):
    # Found categories should be a set of names we actually found in folders
    for split in SPLITS.keys():
        path = os.path.join(BASE_DIR, split)
        if os.path.exists(path):
            shutil.rmtree(path)
        
    for split in SPLITS.keys():
        for category in found_categories:
            path = os.path.join(BASE_DIR, split, category)
            os.makedirs(path, exist_ok=True)

def determine_category(folder_name):
    name = folder_name.lower().strip()
    
    # Check for hazardous items first (Priority)
    if any(x in name for x in ["battery", "bulb", "light", "electronic", "e-waste", "cell", "hazardous"]):
        return "hazardous"

    # Check for other specific material match
    for cat in CATEGORIES:
        if cat in name:
            return cat
            
    # Fallbacks for common alternative names
    if "fruit" in name or "vegetable" in name or "food" in name or "wet" in name:
        return "biological"
    if "bottle" in name or "wrapper" in name:
        return "plastic"
    if "can" in name or "tin" in name:
        return "metal"
            
    return "trash"

def process():
    if not os.path.exists(TEMP_DIR):
        print(f"ERROR: Cannot find folder '{TEMP_DIR}'.")
        return
        
    print(f"\n🚀 Scanning '{TEMP_DIR}' for waste images...")
    
    # First pass: identify which categories exist
    found_categories = set()
    folder_tasks = []

    for root, dirs, files in os.walk(TEMP_DIR):
        images = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not images: continue
            
        folder_name = os.path.basename(root)
        category = determine_category(folder_name)
        found_categories.add(category)
        folder_tasks.append((root, images, category))

    setup_directories(found_categories)
    
    total_count = 0
    counts = {cat: 0 for cat in found_categories}
    
    for root, images, category in folder_tasks:
        print(f"  📁 Found folder '{os.path.basename(root)}' -> Label: {category.upper()}")
        
        random.shuffle(images)
        l = len(images)
        train_end = int(l * SPLITS["train"])
        val_end = train_end + int(l * SPLITS["validation"])
        
        split_map = {
            "train": images[:train_end],
            "validation": images[train_end:val_end],
            "test": images[val_end:]
        }
        
        for split_name, img_list in split_map.items():
            dest_folder = os.path.join(BASE_DIR, split_name, category)
            for img_name in img_list:
                src_path = os.path.join(root, img_name)
                unique_name = f"{uuid.uuid4().hex[:8]}_{img_name}"
                dest_path = os.path.join(dest_folder, unique_name)
                shutil.copy2(src_path, dest_path)
                total_count += 1
                counts[category] += 1
                
    print(f"\n✅ FINISHED!")
    print(f"Total images processed: {total_count}")
    for cat, count in counts.items():
        print(f"  🔹 {cat.capitalize()}: {count}")
    print(f"\nImages are now organized by MATERIAL in the '{BASE_DIR}/' folder ready for training.")

if __name__ == "__main__":
    process()
