import os

def fetch_owned_files(current_path):
    files_and_folders = []

    items = os.listdir(current_path)

    for item in items:
        item_path = os.path.join(current_path, item)
        if os.path.isdir(item_path):
            subfolder_contents = fetch_owned_files(item_path)
            files_and_folders.append([item] + subfolder_contents)
        else:
            files_and_folders.append(item)
    return files_and_folders

def check_peers_file(folder_path):
    if os.path.isdir(folder_path):
        files = fetch_owned_files(folder_path)
    else:
        os.makedirs(folder_path)
        files = []
    return files

# Sử dụng hàm check_peers_file để kiểm tra và lấy danh sách tệp tin
folder_path = "path"
file_list = check_peers_file(folder_path)
print(file_list)