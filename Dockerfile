FROM python:3.8

WORKDIR /code
#COPY . /code
COPY requirements.txt /
RUN pip install -r /requirements.txt

EXPOSE 8080
#CMD ["uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "main.py"]
