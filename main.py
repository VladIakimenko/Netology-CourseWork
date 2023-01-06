from VKLoader import VKLoader
from YaDisk import YaDisk
from create_TOKEN import create_token_file
from datetime import datetime
import requests
import json
import sys
import os


def initiate(path):
    token = read_token(path)
    ya_loader = YaDisk(token['TOKEN']['ya'])
    vk_loader = VKLoader(token['TOKEN']['vk'])
    loaders = {'vk': vk_loader, 'ya': ya_loader}
    return loaders


def read_token(path):
    with open(path, 'rt', encoding='UTF-8') as filehandle:
        token = json.load(filehandle)
    return token


def check_token(path):
    print(f'\tПроверка наличия json токена...')
    invalid = False
    if not os.path.exists(path):
        print(f'\tфайл {path} не обнаружен')
        invalid = True
    else:
        print(f'\t{path} найден. Проверка содержимого файла... ')
        loaders = initiate(path)

        for loader in loaders:
            names = {'ya': 'Яндекс Диск', 'vk': 'vk.com'}
            print()
            print(f'\tПроверка токена {names[loader]}...')
            check = loaders[loader].check_token()
            if check == 'valid':
                print(f'\tТокен {names[loader]} успешно прошёл проверку')
            else:
                invalid = True
                print(f'<error> Токен {names[loader]} не действителен по следующей причине:\n'
                      f'{check}')

    if invalid:
        print()
        print(' ВНИМАНИЕ! Для продолжения работы необходимо создать новый json токен.\n'
              ' Пожалуйста, выполните приведённые ниже инструкции.\n'
              ' При повторных запусках создание токена уже не потребуется.')
        create_token_file(path)

    loaders = initiate(path)
    return loaders


def write_log(action, file_list, path='data/log.json'):
    log = {str(datetime.now()):
           {action: file_list}}
    with open(path, 'at', encoding='UTF-8') as fp:
        json.dump(log, fp=fp, ensure_ascii=False, indent=4)


def vk_get_albums(loader):
    global albums_loaded
    albums_loaded = loader.all_albums()


def ya_get_files(loader):
    global ya_files
    ya_files = loader.get_all()


def ya_show_all(loader, formats=None):
    ya_get_files(loader)
    path = ''
    files = filter_files(ya_files, formats) if formats else ya_files

    for file in files:
        file_path = f"{'/'.join(file['path'].split('/')[:-1])}/"
        if file_path != path:
            path = file_path
            print()
            print(path)
            i = 1
        gap = max([len(item['name']) for item in files]) + 10
        print(f''' {i}. {file['name']}{(gap - len(f" {i}. {file['name']}")) * ' '}|'''
              f'''    {file['type']}{(gap - len(f"    {file['type']}")) * ' '}|'''
              f'''    {round(file['size'] / 1000000, 2)} mb''')
        i += 1
    return ya_files


def vk_show_all(loader, show_system=True):
    vk_get_albums(loader)
    print()
    for i, album in enumerate(albums_loaded):
        if not show_system and album['id'] < 0:
            print(f''' {i + 1}. Системный альбом "{album['title']}" не доступен для загрузки''')
            print()
            continue
        print(f" {i + 1}. Название альбома: {album['title']}")
        print(f" {' ' * (len(str(i + 1)) + 2)}Количество фотографий: {album['size']}")
        print(f" {' ' * (len(str(i + 1)) + 2)}Системный") if album['id'] < 0 \
            else print(f" {' ' * (len(str(i + 1)) + 2)}Дата создания: "
                       f" {datetime.utcfromtimestamp(album['created']).strftime('%d-%m-%Y')}")
        print(f" {' ' * (len(str(i + 1)) + 2)}Количество лайков: {album['likes']}")
        print()


def ya_disk_load(down, loader, obj):
    args = {True: ((loader, obj), (loader, None)),
            False: ((None, obj), (None, None))}
    file_list = objects_to_file_list(*args[down][0]) if obj else form_files_list(*args[down][1])

    if not file_list:
        return

    dest = choose_folder(None) if down else choose_folder(loader)

    counter = 0
    for file in file_list:
        *_, name = file.rpartition('/')

        if down:
            with open(f'{dest}/{name}', 'wb') as f:
                f.write(loader.download_file(file))
        else:
            if loader.exists(f'{dest}/{name}'):
                name = overwrite(dest, name)
            with open(file, 'rb') as f:
                loader.upload_file(f'{dest}/{name}', f)

        counter += 1
        sys.stdout.write('\r' + f' {round((counter * 100) / len(file_list))}%')
        sys.stdout.flush()
    print(f' Загрузка завершена. Загружено файлов: {counter}')
    s = ['c', 'а'] if down else ['на', '']
    write_log(f'Произведена загрузка файлов {s[0]} Яндекс диск{s[1]} в папку {dest}', file_list)


def vk_save(loaders, dest, obj):
    if not dest:
        dest = choose_par1('сохранить фотографии с vk.com', 'vk.com', '')
    if 'albums_loaded' not in globals():
        vk_get_albums(loaders['vk'])
    if not obj:
        vk_show_all(loaders['vk'])
        print(' Выберите альбомы, которые хотите загрузить.')
        print(' Для этого введите номера альбомов через запятую'
              ' или "*", чтобы выбрать все альбомы.\n'
              ' Введите "abort", чтобы выйти в главное меню:')
        obj = input('> ').lower().strip().split(',')
    if '*' in obj:
        album_ids = [album['id'] for album in albums_loaded]
    elif ''.join(obj) == 'abort':
        return
    else:
        album_ids = [albums_loaded[int(i) - 1]['id'] for i in obj if i and i.isdigit()]
    photos = [loaders['vk'].get_photos(album) for album in album_ids]

    args = {
        'local': None,
        'yandex': loaders['ya']
           }
    path = choose_folder(args[dest])

    counter = 0
    for album in photos:
        for name, url in album.items():
            img_data = requests.get(url).content
            if dest == 'local' and os.path.exists(f'{path}/{name}.jpg') or \
               dest == 'yandex' and loaders['ya'].exists(f'{path}/{name}.jpg'):
                name = overwrite(path, name)
            if dest == 'local':
                with open(f'{path}/{name}.jpg', 'wb') as f:
                    f.write(img_data)
            elif dest == 'yandex':
                loaders['ya'].upload_file(f'{path}/{name}.jpg', img_data)
            counter += 1
            len_ = sum([len(album) for album in photos])
            sys.stdout.write('\r' + f' {round((counter * 100) / len_)}%')
            sys.stdout.flush()
    print(f' Загрузка завершена. Загружено фотографий: {counter}')
    s = 'жёсткий диск' if dest == 'local' else 'Яндекс диск'
    write_log(f'Произведено сохранение фотографий из vk.com на {s} в папку {path}',
              [name for album in photos for name in album])


def vk_post(loaders, source):
    if not source:
        source = choose_par1('опубликовать фотографии на vk.com', 'vk.com', 'от')
    if 'albums_loaded' not in globals():
        vk_get_albums(loaders['vk'])

    args = {
        'local': None,
        'yandex': loaders['ya']
           }
    obj = form_files_list(args[source], ('jpg', 'png', 'gif'))
    if not obj:
        return

    vk_show_all(loaders['vk'], False)
    print(' Выберите альбом, в который Вы хотите загрузить фотографии.')
    print(' Введите команду "new", если хотите создать новый.'
          ' Введите "abort", чтобы выйти в главное меню:')
    print()

    while True:
        album = input('> ').strip().lower()

        if album and album.isdigit():
            album = int(album)
            if album in range(1, len(albums_loaded) + 1) \
                    and albums_loaded[int(album) - 1]['id'] > 0:
                album_id = albums_loaded[int(album) - 1]['id']
                break
        elif album == 'abort':
            return
        elif album == 'new':
            print()

            name = ''
            while not name:
                name = input(' Введите название альбома: ')
            description = input(' Введите описание альбома: ')
            album_id = loaders['vk'].create_album(name, description)
            break

    portion = []
    total = 0
    counter_portion = 0
    if not os.path.exists('data/temp'):
        os.makedirs('data/temp')

    for photo in obj:
        if photo.startswith('disk:'):
            f = loaders['ya'].download_file(photo)
            temp_path = f'data/temp/{total}.jpg'
            with open(temp_path, 'wb') as filehande:
                filehande.write(f)
            photo = temp_path
        portion.append(photo)
        total += 1
        counter_portion += 1
        if counter_portion == 5 or photo == obj[-1]:
            loaders['vk'].upload_photos(portion, album_id)
            counter_portion = 0
            portion = []

        sys.stdout.write('\r' + f' {round((total * 100) / len(obj))}%')
        sys.stdout.flush()

    for temp_file in os.listdir('data/temp'):
        os.remove(f'data/temp/{temp_file}')
    os.rmdir('data/temp')

    print(f' Загрузка фотографий завершена. Опубликовано {total} фотографий.')

    if album == 'new':
        vk_get_albums(loaders["vk"])
    s = 'жёсткого диска' if source == 'local' else 'Яндекс диска'
    write_log(f'На сайте vk.com в альбом '
              f'{" ".join([al["title"] for al in albums_loaded if al["id"] == album_id])} '
              f'опубликованы фотографии c {s}:', [photo for photo in obj])


def local_to_file_list(path, formats, file_list):
    if not path:
        path = os.curdir
    if os.path.isdir(path):
        for file in os.listdir(path):
            if os.path.isfile(f'{path}/{file}'):
                full_path = path + f'/{file}'
                file_list.append(full_path)
        if formats:
            file_list = [file for file in file_list if file.split('.')[-1] in formats]
    else:
        if formats and not path.split('/')[-1].split('.')[-1] in formats:
            print(f' Недопустимый формат файла. '
                  f' Вы можете загружать файлы следующих типов: {formats}')
        else:
            if os.path.exists(path):
                file_list.append(path)
            else:
                print()
                print(' Файл по указанному пути не найден.')
                print(' Содержимое каталога:')
                folder = '/'.join(path.split('/')[:-1])
                if not folder:
                    folder = os.curdir
                for file in os.listdir(folder):
                    print(file)
    return file_list


def ya_to_file_list(loader, path, files, file_list, formats):
    if '.' not in path:
        added = False
        for file in files:
            if '/'.join(file['path'].split('/')[:-1]).lstrip('disk:/') \
                                  == path.rstrip('/').lstrip('disk:/'):
                file_list.append(file['path'])
                added = True
        if not added:
            print(f' каталог {path} не найден')
    else:
        if loader.exists(path):
            if formats and not path.split('/')[-1].split('.')[-1] in formats:
                print(f' Недопустимый формат файла. '
                      f' Вы можете загружать файлы следующих типов: {formats}')
            else:
                file_list.append(path)
        else:
            print()
            print(' Файл по указанному пути не найден.')
            print(' Если файл не находится в корневой папке, укажите полный путь.')
    return file_list


def form_files_list(loader, formats):
    file_list = []

    if not loader:
        print('\n Введите путь к файлам на жёстком диске.'
              ' Вводите по одному файлу за раз или укажите папку.')

    elif 'yandex' in loader.host:
        files = ya_show_all(loader, formats)
        print()
        print(' Выберите файлы, которые Вы хотите опубликовать.\n'
              ' Вы можете указать имя каждого файла в отдельности '
              'или указать директорию целиком.')

    print(' Введите команду:\n "end", чтобы закончить ввод файлов,\n'
          ' "clear", чтобы очистить список,\n "abort", чтобы вернуться главное меню.')

    while True:
        print()
        print(" Список файлов:")
        print(*file_list, sep='\n')
        print(f' Файлов в списке: {len(file_list)}')
        print()
        path = input('> ').strip().replace('\\', '/').strip('/')
        if path.lower().strip() == 'end':
            break
        if path.lower().strip() == 'clear':
            file_list = []
            continue
        if path.lower().strip() == 'abort':
            return

        if not loader:
            file_list = local_to_file_list(path, formats, file_list)
        elif 'yandex' in loader.host:
            file_list = ya_to_file_list(loader, path, files, file_list, formats)

    return file_list


def objects_to_file_list(loader, objects):
    file_list = []

    for object_ in objects:
        object_ = object_.strip().replace('\\', '/').strip('/')

        if not loader:
            local_to_file_list(object_, None, file_list)

        elif 'yandex' in loader.host:
            if 'ya_files' not in objects:
                ya_get_files(loader)
            ya_to_file_list(loader, object_, ya_files, file_list, None)
    return file_list


def filter_files(files, formats):
    filtered_files = []
    for file in files:
        match = False
        for extension in formats:
            if extension in file['name']:
                match = True
        if not match:
            continue
        filtered_files.append(file)
    return filtered_files


def overwrite(path, name):
    print(f'\n Файл {path}/{name} уже существует. '
          f' Хотите перезаписать? ("y" или "n")')
    reply = ''
    while reply not in ('y', 'n'):
        reply = input().strip().lower()
    name += '[copy]' if reply == 'n' else ''
    return name


def choose_par1(message, exclusion, from_):
    print()
    print(f'Выберите {from_}куда вы хотите {message}:\n')
    targets = {
        'local': 'жёсткий диск',
        'yandex': 'Яндекс Диск',
        'vk.com': 'ВКонтакте'
              }
    for target in targets:
        if target != exclusion:
            print(f"{target} - {targets[target]}")
    destination = ''
    print()
    while not destination:
        choice = input('> ').strip().lower()
        destination = ''.join([target for target in targets.keys()
                               if target.startswith(choice)
                               and not exclusion.startswith(choice)])
    return destination


def choose_folder(loader):
    path = ''
    print()

    if not loader:
        print(' Введите путь к каталогу на жёстком диске:')
        while True:
            path = input('> ').strip()
            if not path:
                path = os.curdir
            if os.path.exists(path) and os.path.isdir(path):
                break
            else:
                print(f' Папка {path} не найдена. Введите путь к существующей папке')

    elif 'yandex' in loader.host:
        print(' Введите путь к каталогу на Яндекс Диске:')
        path = input('> ').strip()
        if not loader.exists(path):
            print(f' Создан каталог: {loader.create_path(path)}')

    return path


def show_help(path):
    with open(path, 'rt', encoding='UTF-8') as f:
        print(str(f.read()))


def read_cmd(cmd, params, loaders):
    destination = ''
    objects = ''
    targets = ['yandex', 'local']
    if params:
        for target in targets:
            for param in params:
                if target.startswith(param):
                    destination = target
                    params.remove(param)
        if params:
            objects = ' '.join(params).split(',')
        cmd = ' '.join(cmd.split()[:2])

    cmd_list = {
        'help': (show_help, 'data/cmd.info'),
        'vk show': (vk_show_all, loaders['vk']),
        'ya show': (ya_show_all, loaders['ya']),
        'vk save': (vk_save, loaders, destination, objects),
        'vk post': (vk_post, loaders, destination),
        'ya upload': (ya_disk_load, False, loaders['ya'], objects),
        'ya download': (ya_disk_load, True, loaders['ya'], objects)
               }
    return cmd_list.get(cmd)


if __name__ == '__main__':
    loaders = check_token('data/TOKEN/TOKEN.json')

    print('_' * 70)
    print(' введите "help", чтобы увидеть список доступных команд')

    while True:
        print()
        command = input('>>> ').strip()
        if command in ('q', 'quit', 'exit'):
            sys.exit()
        params = command.split()[2:] if len(command.split()) > 2 else None
        cmd = read_cmd(command, params, loaders)
        if cmd:
            function, *arguments = cmd
            function(*arguments)

