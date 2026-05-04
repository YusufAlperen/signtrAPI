FROM python:3.13

WORKDIR /app

# İşletim sistemi seviyesinde gerekli C++ grafik kütüphanelerini kurar
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını ve modelleri kopyala
COPY . .

# FastAPI portunu dışa aç
EXPOSE 8000

# Uygulamayı başlat (Ana dosyanın adının main.py olduğunu varsayıyoruz)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]