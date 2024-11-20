import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
import pandas as pd
from datetime import datetime
import os
import os
import sys

def add_tesseract_to_path():
    """
    Добавляет путь к Tesseract OCR в системную переменную PATH.
    Также устанавливает путь к исполняемому файлу Tesseract для pytesseract.
    """
    # Определение операционной системы
    if os.name == 'nt':  # Windows
        # Укажите фактический путь к Tesseract на вашей системе
        tesseract_path = r'C:\\Tools\\Tesseract-OCR'
        tesseract_executable = os.path.join(tesseract_path, 'tesseract.exe')

        if not os.path.exists(tesseract_executable):
            print(f"Не найден исполняемый файл Tesseract по пути: {tesseract_executable}")
            sys.exit(1)

        # Добавление пути к Tesseract в PATH
        os.environ['PATH'] += os.pathsep + tesseract_path

        # Установка пути к Tesseract для pytesseract
        pytesseract.pytesseract.tesseract_cmd = tesseract_executable
    else:
        # Для Unix-подобных систем предполагается, что Tesseract установлен и доступен в PATH
        # Можно добавить дополнительные проверки при необходимости
        pass

def extract_dates_from_pdf(pdf_path, output_excel='result.xlsx'):
    try:
        # Инициализация списка для хранения результатов
        results = []
        bfound=False
        # Открываем PDF-файл
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()

                # Поиск дат в текстовом содержимом
                dates = extract_dates_from_text(text)
                for date in dates:
                    results.append({
                        "Дата распознавания": datetime.now().strftime("%d.%m.%Y"),
                        "Файл": os.path.basename(pdf_path),
                        "Страница": page_num + 1,
                        "Изображение": -1,
                        "Дата заполнения": date
                    })
                if results: break

                # Извлечение изображений и OCR
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))

                    # Применяем OCR к изображению
                    ocr_text = pytesseract.image_to_string(image, lang='rus')
                    ocr_dates = extract_dates_from_text(ocr_text)
                    for date in ocr_dates:
                        results.append({
                            "Дата распознавания": datetime.now().strftime("%d.%m.%Y"),
                            "Файл": os.path.basename(pdf_path),
                            "Страница": page_num + 1,
                            "Изображение": img_index + 1,
                            "Дата заполнения": date
                        })
                        break
                if results: break

        # Создание DataFrame и запись в Excel
        if results:
            df = pd.DataFrame(results)
            if os.path.exists(output_excel):
                # Если файл уже существует, добавляем данные
                df_existing = pd.read_excel(output_excel)
                df = pd.concat([df_existing, df], ignore_index=True)
            df.to_excel(output_excel, index=False)
            print(f"Данные успешно записаны в {output_excel}")
        else:
            print("Не найдено ни одной даты заполнения.")

    except Exception as e:
        print(f"Ошибка при обработке файла {pdf_path}: {e}")

def extract_dates_from_text(text):
    # Регулярное выражение для поиска дат в формате dd.mm.yyyy
    date_pattern = r'\b(?:Дата\s+заполнения|Дата\s+создания|Дата\s+ввода)\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})\b'
    matches = re.findall(date_pattern, text, re.IGNORECASE)
    return matches

def generate_sber_auth_data(user_id, secret):
        return {"user_id": user_id, "secret": secret}

#from langchain_community.chat_models import GigaChat
from langchain_gigachat.chat_models import GigaChat
import config

os.environ["LANGCHAIN_TRACING_V2"] = "true"

llm = GigaChat(
    credentials=config.GIGA_CHAT_AUTH, 
    verify_ssl_certs=False,
    scope = config.GIGA_CHAT_SCOPE)

from typing import Optional
from pydantic import BaseModel, Field

class Customer(BaseModel):
    """АНКЕТА ЛИЗИНГОПОЛУЧАТЕЛЯ."""

    form_date: Optional[str] = Field(default='ND', description='Дата заполнения')
    customer_name: Optional[str] = Field(default='ND', description='Наименование Лизингополучателя')
    ceo_name: Optional[str] = Field(default='ND', description='ФИО (ЕИО) - ФИО Единого Исполнительного Органа')
    contact_name: Optional[str] = Field(default='ND', description='Контактное лицо (ФИО)')



def extract_client_data_from_pdf(pdf_path, output_excel='result.xlsx'):
    try:
        # Инициализация списка для хранения результатов
        full_content = []
        # Открываем PDF-файл
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                full_content.append(text)

                # Извлечение изображений и OCR
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))

                    # Применяем OCR к изображению
                    ocr_text = pytesseract.image_to_string(image, lang='rus')
                    full_content.append(ocr_text)

        content = '\n==================================================\n'.join(full_content)
        structured_llm = llm.with_structured_output(Customer)
        data = structured_llm.invoke(content)
        print(data)

    except Exception as e:
        print(f"Ошибка при обработке файла {pdf_path}: {e}")


if __name__ == "__main__":
    # Пример использования функции
    pdf_file = 'example.pdf'  # Замените на путь к вашему PDF-файлу
    add_tesseract_to_path()

    #extract_dates_from_pdf(pdf_file)
    extract_client_data_from_pdf(pdf_file)