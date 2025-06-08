import os
import csv
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import openpyxl
import colorama
from colorama import Fore, Style, init

init(autoreset=True)

C_LOGO = Fore.CYAN+Style.BRIGHT
C_HEADER = Fore.YELLOW+Style.BRIGHT
C_MENU_HEADER = Fore.MAGENTA
C_OPTION = Fore.WHITE
C_SUCCESS = Fore.GREEN+Style.BRIGHT
C_PROMPT = Fore.YELLOW
C_ERROR = Fore.RED

load_dotenv()
SCOPE = "user-library-read playlist-read-private"

LOGO = r"""
      ::::::::   ::::::::  ::::    :::     ::: 
    :+:    :+: :+:    :+: :+:+:   :+:   :+: :+:
   +:+        +:+        :+:+:+  +:+  +:+   +:+
  +#++:++#++ +#++:++#++ +#+ +:+ +#+ +#++:++#++:
        +#+        +#+ +#+  +#+#+# +#+     +#+ 
#+#    #+# #+#    #+# #+#   #+#+# #+#     #+#  
########   ########  ###    #### ###     ###   
"""


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace(" ", "_")
    return name[:100]


def pause_and_wait():
    input(f"\n{C_PROMPT}Нажмите Enter, чтобы вернуться в меню...{Style.RESET_ALL}")


def prompt_for_selection(items, item_type_name):

    prompt_text = f"--- Выберите {item_type_name} для выгрузки треков ---"
    print(f"{C_HEADER}{prompt_text}")

    for i, item in enumerate(items, 1):
        details = f" (Владелец: {item['owner']})" if 'owner' in item else f" - {item['artist']}"
        print(f"{C_OPTION}{i}. {item['name']}{details}")

    while True:
        choice_str = input(f"\n{C_PROMPT}Введите номер из списка (или просто Enter для отмены): {Style.RESET_ALL}")
        if not choice_str:
            print("\nОтмена операции.")
            return None

        try:
            choice_num = int(choice_str)
            if 1 <= choice_num <= len(items):
                return items[choice_num - 1]
            else:
                print(f"{C_ERROR}Ошибка: Такого номера нет в списке. Попробуйте еще раз.")
        except ValueError:
            print(f"{C_ERROR}Ошибка: Введите число, а не текст. Попробуйте еще раз.")


def save_to_txt(tracks, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for i, track in enumerate(tracks, 1):
            f.write(f"{i}. {track['name']} - {track['artist']}\n")
    print(f"\n{C_SUCCESS}[+] Список успешно сохранен в файл: {filename}")


def save_to_csv(tracks, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['#', 'Название трека', 'Исполнитель'])
        for i, track in enumerate(tracks, 1):
            writer.writerow([i, track['name'], track['artist']])
    print(f"\n{C_SUCCESS}[+] Список успешно сохранен в файл: {filename}")


def save_to_xlsx(tracks, filename):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Треклист"
    sheet.append(['#', 'Название трека', 'Исполнитель'])
    for cell in sheet["1:1"]: cell.font = openpyxl.styles.Font(bold=True)
    for i, track in enumerate(tracks, 1): sheet.append([i, track['name'], track['artist']])
    for column_cells in sheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = length + 2
    workbook.save(filename)
    print(f"\n{C_SUCCESS}[+] Список успешно сохранен в файл: {filename}")


def ask_and_save_tracks(tracks, source_name, source_type):
    if not tracks:
        print(f"{C_ERROR}Треков для сохранения не найдено.")
        return
    print("─" * 45)
    format_choice = input(
        f"{C_PROMPT}Выберите формат для сохранения (txt, csv, xlsx) или Enter для отмены: {Style.RESET_ALL}").lower()
    if not format_choice:
        print("Сохранение отменено.")
        return
    base_filename = sanitize_filename(f"{source_type}_{source_name}")
    if format_choice == 'txt':
        save_to_txt(tracks, f"{base_filename}.txt")
    elif format_choice == 'csv':
        save_to_csv(tracks, f"{base_filename}.csv")
    elif format_choice == 'xlsx':
        save_to_xlsx(tracks, f"{base_filename}.xlsx")
    else:
        print(f"{C_ERROR}Неверный формат. Сохранение отменено.")


def get_all_user_albums():
    print(f"{C_PROMPT}Загрузка сохраненных альбомов...")
    albums = []
    offset = 0
    while True:
        results = sp.current_user_saved_albums(limit=50, offset=offset)
        if not results['items']: break
        for item in results['items']:
            album = item['album']
            artist_names = ", ".join([artist['name'] for artist in album['artists']])
            albums.append({'id': album['id'], 'name': album['name'], 'artist': artist_names})
        offset += len(results['items'])
        if results['next'] is None: break
    return albums


def get_all_user_playlists():
    print(f"{C_PROMPT}Загрузка плейлистов...")
    playlists = []
    offset = 0
    while True:
        results = sp.current_user_playlists(limit=50, offset=offset)
        if not results['items']: break
        for item in results['items']:
            playlists.append({'id': item['id'], 'name': item['name'], 'owner': item['owner']['display_name']})
        offset += len(results['items'])
        if results['next'] is None: break
    return playlists


def get_tracks_from_album(album_id):
    tracks = []
    offset = 0
    while True:
        results = sp.album_tracks(album_id, limit=50, offset=offset)
        if not results['items']: break
        for item in results['items']:
            artist_names = ", ".join([artist['name'] for artist in item['artists']])
            tracks.append({'name': item['name'], 'artist': artist_names})
        offset += len(results['items'])
        if results['next'] is None: break
    return tracks


def get_tracks_from_playlist(playlist_id):
    tracks = []
    offset = 0
    while True:
        results = sp.playlist_tracks(playlist_id, limit=50, offset=offset)
        if not results['items']: break
        for item in results['items']:
            track = item.get('track')
            if track:
                artist_names = ", ".join([artist['name'] for artist in track['artists']])
                tracks.append({'name': track['name'], 'artist': artist_names})
        offset += len(results['items'])
        if results['next'] is None: break
    return tracks


def get_liked_songs():
    tracks = []
    offset = 0
    while True:
        results = sp.current_user_saved_tracks(limit=50, offset=offset)
        if not results['items']: break
        for item in results['items']:
            track = item.get('track')
            if track:
                artist_names = ", ".join([artist['name'] for artist in track['artists']])
                tracks.append({'name': track['name'], 'artist': artist_names})
        offset += len(results['items'])
        if results['next'] is None: break
    return tracks


def show_faq():
    clear_screen()
    print(f"{C_HEADER}╔════════════════════════════════════════════╗")
    print(f"{C_HEADER}║             FAQ / Помощь                   ║")
    print(f"{C_HEADER}╚════════════════════════════════════════════╝")
    print(f"\n{C_PROMPT}Q: Че за хэ?")
    print(f"{C_OPTION}A: Скрипт коннектится к твоему аккаунту Spotify и позволяет выгружать")
    print(f"{C_OPTION}   списки песен из альбомов, плейлистов и 'Сохраненных треков'")
    print(f"{C_OPTION}   в файлы .txt, .csv или .xlsx.")
    print(f"\n{C_PROMPT}Q: Куда сохраняются файлы?")
    print(f"{C_OPTION}A: В ту же папку, где находится сам скрипт.")
    print(f"\n{C_MENU_HEADER}" + "=" * 25)
    print(f"{C_MENU_HEADER}     by MKultra69")
    print(f"{C_MENU_HEADER}" + "=" * 25)
    pause_and_wait()


def main_menu():
    clear_screen()
    print(f"{C_PROMPT}Подключение к Spotify...")
    try:
        global sp
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
        user = sp.current_user()
        clear_screen()
        # ИСПРАВЛЕННЫЙ СИМВОЛ
        print(f"{C_SUCCESS}[+] Авторизация успешна для: {user['display_name']} [+]\n")
    except Exception as e:
        print(f"{C_ERROR}Ошибка авторизации: {e}")
        exit()

    cached_albums = None
    cached_playlists = None

    while True:
        print(f"{C_LOGO}{LOGO}")
        print(f"{C_HEADER}╔════════════════════════════════════════════╗")
        print(f"{C_HEADER}║              SSNA by MKultra69             ║")
        print(f"{C_HEADER}╚════════════════════════════════════════════╝")

        print(f"\n{C_MENU_HEADER}[ ПРОСМОТР СПИСКОВ ]")
        print(f"{C_OPTION}  1. Показать мои сохраненные альбомы")
        print(f"{C_OPTION}  2. Показать мои плейлисты")
        print(f"\n{C_MENU_HEADER}[ ВЫГРУЗКА В ФАЙЛ ]")
        print(f"{C_OPTION}  3. Выгрузить треки из альбома")
        print(f"{C_OPTION}  4. Выгрузить треки из плейлиста")
        print(f"{C_OPTION}  5. Выгрузить 'Сохраненные треки' (Liked Songs)")
        print(f"\n{C_MENU_HEADER}[ ПРОЧЕЕ ]")
        print(f"{C_OPTION}  6. FAQ / Помощь")
        print(f"{C_OPTION}  0. Выход")
        print("─" * 45)
        choice = input(f"{C_PROMPT}Выберите пункт меню: {Style.RESET_ALL}")
        clear_screen()

        if choice == '1':
            if cached_albums is None: cached_albums = get_all_user_albums()
            print(f"{C_HEADER}--- Ваши сохраненные альбомы ---")
            for i, album in enumerate(cached_albums, 1): print(f"{i}. {album['name']} - {album['artist']}")
            pause_and_wait()

        elif choice == '2':
            if cached_playlists is None: cached_playlists = get_all_user_playlists()
            print(f"{C_HEADER}--- Ваши плейлисты ---")
            for i, pl in enumerate(cached_playlists, 1): print(f"{i}. {pl['name']} (Владелец: {pl['owner']})")
            pause_and_wait()

        elif choice == '3':
            if cached_albums is None: cached_albums = get_all_user_albums()
            selected_album = prompt_for_selection(cached_albums, "альбом")
            if selected_album:
                tracks = get_tracks_from_album(selected_album['id'])
                print(f"\n{C_SUCCESS}[+] Найдено {len(tracks)} треков в альбоме '{selected_album['name']}'.")
                ask_and_save_tracks(tracks, selected_album['name'], "Альбом")
            pause_and_wait()

        elif choice == '4':
            if cached_playlists is None: cached_playlists = get_all_user_playlists()
            selected_playlist = prompt_for_selection(cached_playlists, "плейлист")
            if selected_playlist:
                tracks = get_tracks_from_playlist(selected_playlist['id'])
                print(f"\n{C_SUCCESS}[+] Найдено {len(tracks)} треков в плейлисте '{selected_playlist['name']}'.")
                ask_and_save_tracks(tracks, selected_playlist['name'], "Плейлист")
            pause_and_wait()

        elif choice == '5':
            print(f"{C_PROMPT}Загрузка 'Сохраненных треков'...")
            liked_tracks = get_liked_songs()
            print(f"\n{C_SUCCESS}[+] Найдено {len(liked_tracks)} сохраненных треков.")
            ask_and_save_tracks(liked_tracks, "Liked_Songs", "Сохраненные")
            pause_and_wait()

        elif choice == '6':
            show_faq()

        elif choice == '0':
            print(f"{C_HEADER}Выход из программы. by MKultra69.")
            break

        clear_screen()


if __name__ == "__main__":
    main_menu()