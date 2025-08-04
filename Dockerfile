# Base image ufficiale Python
FROM python:3.11-slim

# Evita input interattivi durante installazione
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Aggiorna pip e installa dipendenze di sistema minime
RUN apt-get update && apt-get install -y build-essential curl && \
    pip install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

# Crea una directory per l'app
WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice sorgente
COPY . .

# Espone la porta su cui gira Uvicorn
EXPOSE 5000

# Comando per lanciare FastAPI con Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
