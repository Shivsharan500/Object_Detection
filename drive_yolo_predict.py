import os
import io
import cv2
import base64
from pathlib import Path
from ultralytics import YOLO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from dotenv import load_dotenv
load_dotenv()


# === CONFIGURATION ===
INPUT_FOLDER_ID = os.getenv("INPUT_FOLDER_ID")
OUTPUT_FOLDER_ID = os.getenv("OUTPUT_FOLDER_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
MODEL_FILE_ID = os.getenv("MODEL_FILE_ID")
      

TMP_DIR = Path(__file__).parent / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# === AUTHENTICATE GOOGLE DRIVE API ===
creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build('drive', 'v3', credentials=creds)

def get_single_drive_image(folder_id):
    print("Collecting the image from drive")
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false",
        fields="files(id, name)",
        pageSize=1
    ).execute()
    files = results.get('files', [])
    return files[0] if files else None

def download_image(file_id, filename):
    print("downloading the image")
    request = drive_service.files().get_media(fileId=file_id)
    local_path = TMP_DIR / filename
    with open(local_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return local_path

def predict_and_save_image_only(model, image_path, output_path):
    print("prediction started")
    results = model.predict(image_path, conf=0.5, augment=True)
    img_with_boxes = results[0].plot()
    cv2.imwrite(str(output_path), img_with_boxes)
    print("predicted and saved")

def upload_image_to_drive(filepath, folder_id):
    print("uploading to drive")
    metadata = {'name': filepath.name, 'parents': [folder_id]}
    media = MediaFileUpload(filepath, mimetype='image/png')
    uploaded = drive_service.files().create(body=metadata, media_body=media, fields='id').execute()
    return uploaded['id']

def delete_drive_file(file_id):
    drive_service.files().delete(fileId=file_id).execute()


def download_model_if_needed(drive_service, file_id, local_path="best.pt"):
    print("Checking for model")
    if os.path.exists(local_path):
        print("best.pt already exists.")
        return

    print("best.pt not found, downloading from Google Drive...")

    request = drive_service.files().get_media(fileId=file_id)
    with open(local_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download progress: {int(status.progress() * 100)}%")

    print("Downloaded best.pt successfully.")


def main():
    print("Prediction Script is Started")

    file = get_single_drive_image(INPUT_FOLDER_ID)
    if not file:
        print("No image found in input folder.")
        return

    file_id = file['id']
    filename = file['name']
    input_path = download_image(file_id, filename)
    output_path = TMP_DIR / f"pred_{filename}"
    
    
    download_model_if_needed(drive_service, MODEL_FILE_ID)

    model = YOLO("best.pt")
    predict_and_save_image_only(model, input_path, output_path)
    
    print(f"Prediction complete. File: {filename}")


    uploaded_file_id = upload_image_to_drive(output_path, OUTPUT_FOLDER_ID)

    # Download predicted image immediately
    request = drive_service.files().get_media(fileId=uploaded_file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    # Save base64 image string to result_base64.txt
    base64_data = base64.b64encode(fh.getvalue()).decode("utf-8")
    with open("result_base64.txt", "w") as f:
        f.write(f"data:image/png;base64,{base64_data}")

    # Cleanup Drive
    delete_drive_file(file_id)
    delete_drive_file(uploaded_file_id)

    # Cleanup local files
    input_path.unlink()
    output_path.unlink()

    print("Python: Prediction complete, result_base64.txt should be written.")

if __name__ == "__main__":
    main()


