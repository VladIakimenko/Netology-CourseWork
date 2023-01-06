import time
import requests


class YaDisk:
    host = 'https://cloud-api.yandex.net:443'

    def __init__(self, token):
        self.headers = {'Authorization': f'OAuth {token}'}

    def check_token(self):
        """
        Method sends a test request (meta info on user's disk)
        :return: returns 'valid' or error message from server
        """
        uri = '/v1/disk'
        headers = self.headers
        response = requests.get(self.host + uri, headers=headers)
        return 'valid' if response.status_code == 200 else response.json().get('message')

    def upload_file(self, path, file):
        """
        path: Path and filename at Yandex Disk. All folders in path must exist.
                     Missing folders can be created with create_folder method.
        file: File opened in 'rb' mode. One at a time.
        :return: Path to file at Yandex Disk
                 Prints out (not returns) a mistake code if any
        """
        url = self.__get_upload_link(path)
        params = {'path': path}
        files = {'file': file}
        response = requests.put(url, headers=self.headers, params=params, files=files)
        if response.status_code == 201:
            return path
        else:
            print(f'Ошибка {response.status_code}')

    def __get_upload_link(self, path, overwrite=True):
        """
        Gets a link required to upload a file. Each file - separate link.
        path: Destination path at Yandex Disk
        overwrite: 'True' if a file with same filename is to be overwritten.
                   Method will not work if 'False' and names coincide.
        :return: Returns an upload link (required for upload_file method)
                 Prints out (not returns) a mistake code if any
        """
        uri = '/v1/disk/resources/upload'
        params = {'path': path, 'overwrite': overwrite}
        response = requests.get(self.host + uri, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()['href']
        else:
            print(f'Ошибка {response.status_code}')

    def exists(self, path):
        """
        Checks existence of file or folder.
        path: Destination path and filename
        :return: 'False' if such file or dir does not exist. 'True' if it does.
        """
        uri = '/v1/disk/resources'
        params = {'path': path}
        response = requests.get(self.host + uri, headers=self.headers, params=params)
        return False if response.status_code == 404 else True

    def create_folder(self, path):
        """
        Creates a folder at Yandex Disk. Supports only 1 level of depth.
        All alongside folders must be created separately.
        path: Destination folder name.
        :return: Destination path
                 Prints out (not returns) a mistake code if any
        """
        uri = '/v1/disk/resources'
        params = {'path': path}
        response = requests.put(self.host + uri, headers=self.headers, params=params)
        if response.status_code == 201:
            return path
        else:
            print(f'Ошибка {response.status_code}')

    def create_path(self, path):
        """
        Puts together a process of checking existence and creation of folders
        all along the path if they are missing.
        path: Full path at Yandex Disk to destination folder and its name.
        :return: Resulting path (should be equal to param path if no mistakes occurred)
        """
        res_path = ''
        for folder in path.rstrip('/').lstrip('/').split('/'):
            res_path += '/' + folder
            if not self.exists(res_path):
                self.create_folder(res_path)
        return res_path

    def get_all(self):
        """
        :return: Returns a sorted by paths list of all files:
            [{'json': {the original json from server},
              'name': file name
              'path': path to file at YaDisk
              'size': size in bytes
              'type': file type},
             ...]
        """
        uri = '/v1/disk/resources/files'
        headers = self.headers
        params = {'limit': 1000}
        response = requests.get(self.host + uri, headers=headers, params=params)
        file_list = []
        for i, item in enumerate(response.json().get('items')):
            file_list.append({})
            file_list[i]['name'] = item.get('name')
            file_list[i]['type'] = item.get('mime_type')
            file_list[i]['path'] = item.get('path')
            file_list[i]['size'] = item.get('size')
            file_list[i]['json'] = item
        return sorted(file_list, key=(lambda x: x.get('path')), reverse=True)

    def download_file(self, path):
        """
        path: to file at YaDisk
        :return: byte-type object with file
        """
        url = self.__get_download_link(path)
        response = requests.get(url)
        return response.content

    def __get_download_link(self, path):
        """
        path: to file at YaDisk
        :return: link to download the file
        """
        uri = '/v1/disk/resources/download'
        params = {'path': path}
        response = requests.get(self.host + uri, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()['href']
        else:
            print(f'Ошибка {response.status_code}')


