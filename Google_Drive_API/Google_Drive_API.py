import io
import os.path
import google.auth
import mimetypes
import telebot
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]

def upload_file(file_name):
  global creds
  
  if not os.path.exists(file_name):
    return("Файл із заданим ім'ям не було знайдено.")

  try:
    service = build("drive", "v3", credentials=creds)
    
    mime_type, _ = mimetypes.guess_type(file_name)
    
    file_metadata = {
        "name": file_name,
        "mimeType": mime_type,
    }
    
    media = MediaFileUpload(file_name, mimetype=mime_type, resumable=True)
    
    file = (service.files().create(body=file_metadata, media_body=media, fields="id").execute())
    
    return(f'Файл з ID: {file.get("id")} був завантажений.')

  except HttpError as error:
    print(f"An error occurred: {error}")
    file = None
   

def download_file(file_name):
  global creds
  
  try:
    service = build("drive", "v3", credentials=creds)
  
    query = "'root' in parents and mimeType != 'application/vnd.google-apps.folder'"
    results = (
        service.files()
        .list(q=query, fields="nextPageToken, files(id, name)")
        .execute()
    )
    items = results.get("files", [])
  
    file_id = None
    for item in items:
      if item['name'] == file_name:
        file_id = item['id']  
      
    if file_id == None:
      return("Файл із заданим ім'ям не було знайдено.")
  
    request = service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
      status, done = downloader.next_chunk()
    #  print(f"Завантажено {int(status.progress() * 100)}%.")
    
    with open(file_name, "wb") as f:
      f.write(file.getvalue())
      
    return("Файл був завантажений з диска.")

  except HttpError as error:
    print(f"An error occurred: {error}")
    file = None
  
    
def output_of_files():
  global creds

  try:
    service = build("drive", "v3", credentials=creds)

    results = service.files().list(q="'root' in parents", fields="files(name, mimeType, modifiedTime, size)").execute()
    items = results.get('files', [])

    ans = ""

    if not items:
      return('Файли не знайдені.')
    else:
      ans += 'Файли та папки, які знаходяться у кореневій папці:\n'  
      ans += 'Назва | Тип | Дата останньої зміни | Розмір\n'
      ans += '---------------------------------------------------\n'
      for item in items:
        name = item['name']
        mime_type = item['mimeType']
        modified_time = datetime.strptime(item['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")
        size = item.get('size', '0')
        size = f"{size} bytes" if size.isdigit() else "Unknown"
        file_type = "Файл" if mime_type != "application/vnd.google-apps.folder" else "Папка"
        ans += f"{name} | {file_type} | {modified_time} | {size}\n"
        
    return(ans)
  
  except HttpError as error:
    print(f"An error occurred: {error}")


def create_folder(folder_name):
  global creds
  
  try:
    service = build("drive", "v3", credentials=creds)
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    file = service.files().create(body=file_metadata, fields="id").execute()
    return(f'Папка з ID: {file.get("id")} була створена.')

  except HttpError as error:
    print(f"An error occurred: {error}")


def delete_file(file_name):
  global creds

  try:
    service = build("drive", "v3", credentials=creds)

    results = service.files().list(q="'root' in parents", fields="files(id, name)").execute()
    items = results.get("files", [])

    file_id = None
    for item in items:
      if item['name'] == file_name:
        file_id = item['id']  

    if file_id == None:
      return("Файл (папку) із заданим ім'ям не було знайдено.")

    body_value = {'trashed': True}
    response = service.files().update(fileId=file_id, body=body_value).execute()
    return("Файл (папку) із заданим ім'ям було переміщено у кошик.")

  except HttpError as error:
    print(f"An error occurred: {error}")


#def change_folder(folder_name)
#current_folder_id = 'root'

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=8080)


bot = telebot.TeleBot('6960142159:AAEDU8APXxqXS6YF2KJ5vBcVhC9piLod_Q4')

@bot.message_handler(commands=['start'])
def start(message):
  bot.send_message(message.chat.id, "Уведіть одну з команд:\n"\
                                    "/upload - завантаження файлу на диск;\n"\
                                    "/download - завантаження файлу з диска;\n"\
                                    "/output - виведення інформації про файли;\n"\
                                    "/create - створення папки;\n"\
                                    "/delete - видалення файлу (папки).")

@bot.message_handler(commands=['upload'])
def upload(message):
  bot.send_message(message.chat.id, "Уведіть назву файлу.")
  bot.register_next_step_handler(message, upload_results)
  
def upload_results(message):
  bot.send_message(message.chat.id, upload_file(message.text))


@bot.message_handler(commands=['download'])
def download(message):
  bot.send_message(message.chat.id, "Уведіть назву файлу.")
  bot.register_next_step_handler(message, download_results)

def download_results(message):
  bot.send_message(message.chat.id, download_file(message.text))


@bot.message_handler(commands=['output'])
def output(message):
  bot.send_message(message.chat.id, output_of_files())


@bot.message_handler(commands=['create'])
def create(message):
  bot.send_message(message.chat.id, "Уведіть назву папки.")
  bot.register_next_step_handler(message, create_results)

def create_results(message):
  bot.send_message(message.chat.id, create_folder(message.text))


@bot.message_handler(commands=['delete'])
def delete(message):
  bot.send_message(message.chat.id, "Уведіть назву файлу (папки).")
  bot.register_next_step_handler(message, delete_results)

def delete_results(message):
  bot.send_message(message.chat.id, delete_file(message.text))


bot.polling(none_stop=True)