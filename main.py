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
#from langchain_community.chat_models import GigaChat
from langchain_core.prompts import ChatPromptTemplate
from langchain_gigachat.chat_models import GigaChat
from langchain_openai import ChatOpenAI
from typing import Optional, List
from pydantic import BaseModel, Field

import config

os.environ["LANGCHAIN_TRACING_V2"] = "true"


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


class Company(BaseModel):
    """Компания группы"""

    company_name: Optional[str] = Field(default='ND', description='Наименование')
    company_inn: Optional[str] = Field(default='ND', description='ИНН')

class BusinessType(BaseModel):
    """Вид деятельности Лизингополучателя"""

    business_name: Optional[str] = Field(default='ND', description='Вид деятельности')
    business_ratio: Optional[str] = Field(default='ND', description='Доля в структуре выручки')

class PersonalDocumentInfo(BaseModel):
    """Сведения о документе, удостоверяющем личность"""

    name: Optional[str] = Field(default='ND', description='Наименование')
    seria: Optional[str] = Field(default='ND', description='Серия')
    number: Optional[str] = Field(default='ND', description='Номер')
    issue_date: Optional[str] = Field(default='ND', description='Дата выдачи')
    issuer: Optional[str] = Field(default='ND', description='Кем выдан')
    issuer_dep: Optional[str] = Field(default='ND', description='Код подразделения')
    registration_address: Optional[str] = Field(default='ND', description='Адрес регистрации')

class CEOInfo(BaseModel):
    """ИНФОРМАЦИЯ О ЕДИНОМ ИСПОЛНИТЕЛЬНОМ ОРГАНЕ"""

    managing_company: Optional[str] = Field(default='ND', description='Управляющая компания')
    name: Optional[str] = Field(default='ND', description='ФИО')
    birthday: Optional[str] = Field(default='ND', description='Дата рождения')
    citizenship: Optional[str] = Field(default='ND', description='Гражданство')
    inn: Optional[str] = Field(default='ND', description='ИНН')
    email: Optional[str] = Field(default='ND', description='E-mail')
    phone: Optional[str] = Field(default='ND', description='Телефон')
    birthplace: Optional[str] = Field(default='ND', description='Место рождения')
    personal_document: Optional[PersonalDocumentInfo] = Field(..., description="Сведения о документе, удостоверяющем личность")
    is_beneficiary_owner: Optional[bool] = Field(default=False, description='Является бенефициарным владельцем')
    is_foreighn_official: Optional[bool] = Field(default=False, description='Не является иностранным публичным должностным лицом или родтственником')
    is_international_official: Optional[bool] = Field(default=False, description='Не является должностным лицом публичных международных организаций')
    is_local_official: Optional[bool] = Field(default=False, description='Не является публичным должностным лицом Российской Федерации')

class CustomerBusiness(BaseModel):
    """ИНФОРМАЦИЯ О БИЗНЕСЕ ЛИЗИНГОПОЛУЧАТЕЛЯ"""

    employees_count: Optional[int] = Field(default='ND', description='Численность сотрудников')
    is_group: Optional[bool] = Field(default=True, description='Входит ли в группу взаимосвязанных компаний?')
    group_companies: Optional[List[Company]] = Field(..., description="Перечень компаний группы")
    businesses: Optional[List[BusinessType]] = Field(..., description="Основные виды деятельности Лизингополучателя")
    comment: Optional[str] = Field(default='ND', description='Комментарий к виду деятельности')
    is_online: Optional[bool] = Field(default=True, description='Есть сайт и/или страницы в социальных сетях')


class BeneficiaryInfo(BaseModel):
    """Сведения о бенефициарных владельцах"""

    name: Optional[str] = Field(default='ND', description='ФИО')
    birthday: Optional[str] = Field(default='ND', description='Дата рождения')
    citizenship: Optional[str] = Field(default='ND', description='Гражданство')
    inn: Optional[str] = Field(default='ND', description='ИНН')
    capital_ratio: Optional[str] = Field(default='ND', description='Доля в уставном капитале (%)')
    birthplace: Optional[str] = Field(default='ND', description='Место рождения')
    personal_document: Optional[PersonalDocumentInfo] = Field(..., description="Сведения о документе, удостоверяющем личность")

class DebtInto(BaseModel):
    """ИНФОРМАЦИЯ О ЗАДОЛЖЕННОСТИ"""

    debt_type: Optional[str] = Field(default='ND', description='Вид обязательств')
    creditor: Optional[str] = Field(default='ND', description='Кредитор')
    currency: Optional[str] = Field(default='ND', description='Валюта')
    start_date: Optional[str] = Field(default='ND', description='Дата выдачи')
    end_date: Optional[str] = Field(default='ND', description='Дата окончания')
    debt_amount: Optional[str] = Field(default='ND', description='Сумма договора')
    debt_due: Optional[str] = Field(default='ND', description='Остаток задолженности')
    debt_outstanding: Optional[str] = Field(default='ND', description='Сумма к погашению')
    debt_collateral: Optional[str] = Field(default='ND', description='Обеспечение')

class DebtTotalInto(BaseModel):
    """ИНФОРМАЦИЯ О ТИПЕ ЗАДОЛЖЕННОСТИ"""

    debt_type: Optional[str] = Field(default='ND', description='Вид обязательств')
    debts: Optional[List[DebtInto]] = Field(..., description="ИНФОРМАЦИЯ О ЗАДОЛЖЕННОСТИ]")
    debt_total_amount: Optional[str] = Field(default='ND', description='Общая сумма договора по типу задолженности')
    debt_due: Optional[str] = Field(default='ND', description='Общий остаток задолженности по типу задолженности')
    debt_outstanding: Optional[str] = Field(default='ND', description='Общая сумма к погашению по типу задолженности')


class Customer(BaseModel):
    """АНКЕТА ЛИЗИНГОПОЛУЧАТЕЛЯ."""

    form_date: Optional[str] = Field(default='ND', description='Дата заполнения')
    customer_name: Optional[str] = Field(default='ND', description='Наименование Лизингополучателя')
    ceo_name: Optional[str] = Field(default='ND', description='ФИО (ЕИО) - ФИО Единого Исполнительного Органа')
    contact_name: Optional[str] = Field(default='ND', description='Контактное лицо (ФИО)')
    contact_phone: Optional[str] = Field(default='ND', description='Телефон контактного лица')
    contact_phone: Optional[str] = Field(default='ND', description='Телефон контактного лица')
    contact_email: Optional[str] = Field(default='ND', description='E-mail контактного лица')
    customer_phone: Optional[str] = Field(default='ND', description='Телефон организации')
    customer_inn: Optional[str] = Field(default='ND', description='ИНН Лизингополучателя')
    customer_ogrn: Optional[str] = Field(default='ND', description='ОГРН Лизингополучателя')
    customer_tax_method: Optional[str] = Field(default='ND', description='Система налогообложения')
    customer_post_address: Optional[str] = Field(default='ND', description='Фактический адрес')
    customer_official_address: Optional[str] = Field(default='ND', description='Почтовый адрес')
    customer_email: Optional[str] = Field(default='ND', description='E-mail Лизингополучателя')
    customer_email: Optional[str] = Field(default='ND', description='E-mail Лизингополучателя')
    cert_center: Optional[str] = Field(default='ND', description='Предпочтительный провайдер ЭЦП')
    is_beneficiary: Optional[bool] = Field(default=True, description='Является выгодоприобретателем')
    customer_business_info: Optional[CustomerBusiness] = Field(..., description="Информация о бизнесе Лизингополучателя")
    ceo_info: Optional[CEOInfo] = Field(..., description="ИНФОРМАЦИЯ О ЕДИНОМ ИСПОЛНИТЕЛЬНОМ ОРГАНЕ")
    beneficiaries: Optional[List[BeneficiaryInfo]] = Field(default=None,  description="Сведения о бенефициарных владельцах")
    debts: Optional[List[DebtTotalInto]] = Field(default=None, description="ИНФОРМАЦИЯ О КРЕДИТНОЙ ИСТОРИИ И ДОЛГОВОЙ НАГРУЗКЕ]")


prompt_text = """
Extract the desired information from the following passage.

Only extract the properties mentioned in the 'Customer' function.

Contract:
{form}
"""

#llm = GigaChat(
#    credentials=config.GIGA_CHAT_AUTH, 
#    verify_ssl_certs=False,
#    scope = config.GIGA_CHAT_SCOPE)
llm = ChatOpenAI(openai_api_key=config.OPENAI_API_KEY, model='gpt-4o-mini', temperature=0.1)
prompt = ChatPromptTemplate.from_template(prompt_text)
structured_llm = llm.with_structured_output(Customer)
recogn_chain = prompt | structured_llm

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
        
        data = recogn_chain.invoke(content)
        print(data)

    except Exception as e:
        print(f"Ошибка при обработке файла {pdf_path}: {e}")


if __name__ == "__main__":
    # Пример использования функции
    pdf_file = 'example.pdf'  # Замените на путь к вашему PDF-файлу
    add_tesseract_to_path()

    #extract_dates_from_pdf(pdf_file)
    extract_client_data_from_pdf(pdf_file)