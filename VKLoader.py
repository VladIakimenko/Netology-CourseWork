import requests
from datetime import datetime
from time import sleep


class VKLoader:
    host = 'https://api.vk.com'

    def __init__(self, token):
        self.params = {'access_token': token, 'v': '5.131'}

    def check_token(self):
        """
        Method sends a test request (receiving the list of albums)
        :return: returns 'valid' or error message from server
        """
        url = self.host + '/method/photos.getAlbums'
        params = self.params
        response = requests.get(url, params=params)
        return 'valid' if response.json().get('response') \
                       else response.json()['error']['error_msg']

    def create_album(self, title, description=''):
        """
        title: takes the name of the album as an argument
        description: description of an album
        :return: returns album id (which is required for most API operations with photos)
        """
        url = self.host + '/method/photos.createAlbum'
        params = {**{'title': title, 'description': description}, **self.params}
        response = requests.post(url, params=params)
        return response.json()['response']['id']

    def upload_photos(self, file_list, album=''):
        """
        Puts together the whole process of uploading photographs
        album: album id received from create_album method
        file_list: list of 5 items maximum containing str paths to local files
        :return: "success" or "error"
                  depending on the __save_picture method request.status_code
        """
        if not album:
            album = self.create_album(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
        upload_url = self.__photos_get_server(album)
        *upload_data, = self.__send_picture(upload_url, file_list)
        return self.__save_picture(album, *upload_data)

    def __photos_get_server(self, album):
        """
        album: album id received from create_album method
        :return: upload link required to upload photos or other content
        """
        url = self.host + '/method/photos.getUploadServer'
        params = {**{'album_id': album}, **self.params}
        response = requests.get(url, params=params)
        if response.json().get('error'):
            print(response.json().get('error').get('error_msg'))
        return response.json()['response']['upload_url']

    def __send_picture(self, upload_url, file_list):
        """
        upload_url: upload_url recieved from __photos_get_server method
        file_list: list of 5 items maximum containing str paths to local files
        :return: 3 params, required for save_picture function (that finalizes the process)
        """
        url = upload_url
        files_dict = {}
        for i, path in enumerate(file_list):
            files_dict[f'file{i + 1}'] = (path, open(path, 'rb'), "multipart/form-data")
        response = requests.post(url,
                                 params=self.params,
                                 files=files_dict)
        return (
                response.json()['server'],
                response.json()['photos_list'],
                response.json()['hash']
               )

    def __save_picture(self, album_id, s_server, s_photos_list, s_hash, caption=''):
        """
        album_id: album id received from create_album method
        s_server: received from __send_picture method
        s_photos_list: received from __send_picture method
        s_hash: received from __send_picture method
        caption: A caption to the photo. Can be filled in or left blank.
        :return: "success" or "error" depending on the response.status_code
        """
        url = self.host + '/method/photos.save'
        params = {**{'album_id': album_id,
                     'server': s_server,
                     'photos_list': s_photos_list,
                     'hash': s_hash,
                     'caption': caption},
                  **self.params}
        response = requests.post(url, params=params)
        return 'success' if response.status_code == 200 else 'error'

    def __get_album(self, album, extended=True):
        """
        Prvidws full details on an album
        album: album id
        extended: show additional details (likes, etc...)
        :return: a dict with full data on an album
        """
        url = self.host + '/method/photos.get'
        params = {**{'album_id': album, 'extended': extended}, **self.params}
        response = requests.get(url, params=params)
        return response.json()

    def all_albums(self, system=True):
        """
        system: whether to include system albums (like wall, saved, etc...)
        :return: returns a list with dics with info an all albums:
        [{'created': date of creation (if not System),
          'id': unique album id - required for most methods
          'likes': amount of likes
          'size': amount of photos in album
          'title': album's name},
          ...]
        """
        url = self.host + '/method/photos.getAlbums'
        params = {**{'need_system': system}, **self.params}
        response = requests.get(url, params=params)
        if response.json().get('error'):
            print(response.json().get('error').get('error_msg'))
        album_list = []
        index = 0
        for album in response.json()['response']['items']:
            album_data = self.__get_album(album.get('id'))
            if not album_data.get('error'):
                album_list.append({})
                album_list[index]['id'] = album['id']
                album_list[index]['title'] = album['title']
                album_list[index]['size'] = album['size']
                album_list[index]['created'] = album.get('created')
                album_list[index]['likes'] = \
                    album_data['response']['items'][0]['likes']['count'] \
                        if len(album_data['response']['items']) > 0 else 0
                index += 1
        return album_list

    def get_photos(self, album):
        """
        album: album id
        :return: returns a dict with links to photos from album (max sized):
            {'unique photo number(number of likes)': link to photo,
            ...}
        """
        response = self.__get_album(album)
        photos_dict = {}
        if response.get('error'):
            print(response.get('error').get('error_code'))
        else:
            for i, item in enumerate(response['response']['items']):
                photos_dict[f"{item['id']}({item['likes']['count']} likes)"] \
                    = item['sizes'][-1]['url']
        return photos_dict

