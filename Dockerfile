FROM continuumio/miniconda3:24.9.2-0

WORKDIR /app

COPY requirements.txt /app

RUN apt-get update && apt-get install -y
    
RUN conda install -y -c conda-forge python=3.12.7

RUN pip install -r requirements.txt

COPY . /app

CMD ["python3", "main.py"]