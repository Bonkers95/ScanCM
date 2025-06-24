"""
Script OCR amélioré : détection automatique de la Virtual Camera Camo et gestion des langues Tesseract.
Le script essaie d'abord le français, puis l'anglais en fallback si le pack de langue française est absent.
"""
import os
import time
import cv2
import pytesseract
import webbrowser
import traceback
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# Configuration Tesseract
TESS_PATH = r"C:\\Program Files\\Tesseract-OCR"
os.environ["TESSDATA_PREFIX"] = os.path.join(TESS_PATH, "tessdata")
pytesseract.pytesseract.tesseract_cmd = os.path.join(TESS_PATH, "tesseract.exe")

# Recherche automatique de la caméra (Camo ou autre)
def open_camera(max_index=5, backends=None):
    if backends is None:
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    names = ["video=Reincubate Camo", "video=Camo Virtual Camera", "video=Camo"]
    for name in names:
        for backend in backends:
            cap = cv2.VideoCapture(name, backend)
            if cap.isOpened():
                print(f"🔍 Caméra trouvée name='{name}', backend={backend}")
                return cap, name, backend
            cap.release()
    for idx in range(max_index):
        for backend in backends:
            cap = cv2.VideoCapture(idx, backend)
            if cap.isOpened():
                print(f"🔍 Caméra trouvée index={idx}, backend={backend}")
                return cap, idx, backend
            cap.release()
    return None, None, None

cap, source, used_backend = open_camera()
if cap is None:
    messagebox.showerror("Caméra non trouvée", "Aucune caméra disponible. Vérifiez que Camo Studio est ouvert ou qu'une webcam est branchée.")
    raise SystemExit
print(f"🔧 Utilisation de la source '{source}' avec backend={used_backend}")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
focus_available = cap.set(cv2.CAP_PROP_AUTOFOCUS, 0) and cap.set(cv2.CAP_PROP_FOCUS, 30)

root = tk.Tk()
root.title("📷 Lorcana Card Scanner OCR")
frame_left = tk.Frame(root)
frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
ocr_status = tk.Label(frame_left, text="", fg="red")
ocr_status.pack(pady=5)

canvas = tk.Canvas(root)
canvas.pack(fill=tk.BOTH, expand=True)

rectangle_id = None
selected_zone = None
start_point = end_point = None
drawing = False
rotation_angle = 0

def process_ocr():
    global selected_zone
    ocr_status.config(text="")
    if not selected_zone:
        ocr_status.config(text="❗ Aucune zone sélectionnée.")
        return
    x1, y1 = selected_zone[0]
    x2, y2 = selected_zone[1]
    x1, x2 = sorted([x1, x2])
    y1, y2 = sorted([y1, y2])
    ret, frame = cap.read()
    if not ret:
        ocr_status.config(text="⚠️ Impossible de lire la caméra.")
        return
    if rotation_angle == 90:
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_angle == 180:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    h, w = frame.shape[:2]
    scale_x = w / canvas.winfo_width()
    scale_y = h / canvas.winfo_height()
    rx1, rx2 = int(x1 * scale_x), int(x2 * scale_x)
    ry1, ry2 = int(y1 * scale_y), int(y2 * scale_y)
    if rx1 >= rx2 or ry1 >= ry2:
        ocr_status.config(text="❌ Zone invalide pour OCR.")
        return
    roi = frame[ry1:ry2, rx1:rx2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.medianBlur(gray, 3)
    print("🔍 Taille de l'image OCR :", gray.shape)
    text = ""
    for lang in ["fra", "eng"]:
        try:
            text = pytesseract.image_to_string(gray, lang=lang).strip()
            if text:
                print(f"🧾 Texte détecté ({lang}):", text)
                break
        except pytesseract.TesseractError as e:
            print(f"⚠️ Impossible de charger la langue '{lang}': {e}")
            continue
    if not text:
        ocr_status.config(text="❌ Aucun texte détecté ou pack Tesseract manquant.")
        return
    query = text.replace("\n", " ").replace("’", "'")
    url = f"https://www.cardmarket.com/fr/Lorcana/Products/Search?searchString={query.replace(' ', '+')}"
    print("🔎 Recherche :", url)
    webbrowser.open(url)

def rotate_cam():
    global rotation_angle
    rotation_angle = (rotation_angle + 90) % 360
    rotate_label.config(text=f"🔄 Rotation: {rotation_angle}°")

def on_mouse_down(e):
    global drawing, start_point, end_point
    drawing = True
    start_point = (e.x, e.y)
    end_point = start_point

def on_mouse_up(e):
    global drawing, selected_zone, end_point
    drawing = False
    end_point = (e.x, e.y)
    selected_zone = (start_point, end_point)
    print(f"✅ Zone: {selected_zone}")

def on_mouse_move(e):
    global end_point
    if drawing:
        end_point = (e.x, e.y)

def update():
    ret, frame = cap.read()
    if ret:
        if rotation_angle == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation_angle == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        h, w = frame.shape[:2]
        nw, nh = canvas.winfo_width(), canvas.winfo_height()
        img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((nw, nh)))
        canvas.imgtk = img
        canvas.create_image(0, 0, anchor=tk.NW, image=img)
        if start_point and end_point:
            canvas.delete("rect")
            canvas.create_rectangle(*start_point, *end_point, outline="green", width=2, tags="rect")
    root.after(30, update)

tk.Button(frame_left, text="📸 Scanner (OCR)", command=process_ocr).pack(pady=10)
tk.Button(frame_left, text="🔁 Tourner caméra", command=rotate_cam).pack(pady=5)
rotate_label = tk.Label(frame_left, text="🔄 Rotation: 0°")
rotate_label.pack(pady=2)

tk.Label(frame_left, text=("🎚️ Focus manuel" if focus_available else "❌ Focus non supporté")).pack(pady=5)
if focus_available:
    def set_focus(v): cap.set(cv2.CAP_PROP_FOCUS, int(v))
    slider = tk.Scale(frame_left, from_=0, to=255, orient=tk.HORIZONTAL, command=set_focus)
    slider.set(30)
    slider.pack(pady=5)

canvas.bind("<Button-1>", on_mouse_down)
canvas.bind("<ButtonRelease-1>", on_mouse_up)
canvas.bind("<B1-Motion>", on_mouse_move)
canvas.bind("<Button-3>", lambda e: process_ocr())

update()
root.mainloop()
cap.release()
