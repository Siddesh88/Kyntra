from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil, os
import cv2
from deepface import DeepFace
import pytesseract
from fpdf import FPDF
from PIL import Image

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_id_info(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    name, dob, id_type = "", "", ""

    for line in text.split("\n"):
        if "DOB" in line or "Birth" in line:
            dob = line.strip()
        if any(x in line.upper() for x in ["AADHAAR", "GOVT", "INDIA"]):
            id_type = "Aadhaar"
        if any(x in line.upper() for x in ["INCOME", "TAX", "PAN"]):
            id_type = "PAN"
        if len(line.strip().split()) >= 2 and name == "":
            name = line.strip()
    return name, dob, id_type

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/verify", response_class=HTMLResponse)
async def verify(request: Request, selfie: UploadFile = File(...), idcard: UploadFile = File(...)):
    selfie_path = os.path.join(UPLOAD_FOLDER, "selfie.jpg")
    idcard_path = os.path.join(UPLOAD_FOLDER, "idcard.jpg")

    with open(selfie_path, "wb") as f:
        shutil.copyfileobj(selfie.file, f)
    with open(idcard_path, "wb") as f:
        shutil.copyfileobj(idcard.file, f)

    try:
        result = DeepFace.verify(selfie_path, idcard_path)
        face_match = result["verified"]
    except Exception:
        face_match = False

    name, dob, id_type = extract_id_info(idcard_path)

    pdf_path = os.path.join("static", "KYC_Report.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="KYNTRA KYC Verification Report", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Name: {name}", ln=True)
    pdf.cell(200, 10, txt=f"DOB: {dob}", ln=True)
    pdf.cell(200, 10, txt=f"ID Type: {id_type}", ln=True)
    pdf.cell(200, 10, txt=f"Face Match: {'✅ Match' if face_match else '❌ No Match'}", ln=True)
    pdf.output(pdf_path)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "name": name,
        "dob": dob,
        "id_type": id_type,
        "face_match": face_match
    })