import shutil
import os


import os
import shutil

def delete_folder(folder_path):
    """
    Deletes a folder and all its contents.

    Args:
        folder_path (str): The path to the folder to be deleted.

    Returns:
        bool: True if the folder was successfully deleted, False otherwise.
    """
    try:
        if os.path.exists(folder_path):
            # TODO: fix permission
            shutil.rmtree(folder_path)
            return True
        else:
            print(f"Folder '{folder_path}' does not exist.")
            return False
    except PermissionError:
        print(f"Permission denied: Unable to delete '{folder_path}'.")
        return False
    except Exception as e:
        print(f"An error occurred while deleting '{folder_path}': {e}")
        return False
