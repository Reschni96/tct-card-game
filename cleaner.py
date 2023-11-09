import os
import time

# Define the directory and the age threshold
data_archive_dir = 'data_archive'
age_threshold_in_seconds = 7 * 24 * 60 * 60  # 1 week

# Get the current time
current_time = time.time()

# Iterate over files in the directory
for filename in os.listdir(data_archive_dir):
    file_path = os.path.join(data_archive_dir, filename)

    # Check if the file is older than the threshold
    file_age = current_time - os.path.getmtime(file_path)
    if file_age > age_threshold_in_seconds:
        try:
            # Delete the file
            os.remove(file_path)
            print(f"Deleted old file: {file_path}")
        except Exception as e:
            print(f"Failed to delete {file_path}: {str(e)}")
