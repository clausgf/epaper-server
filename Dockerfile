FROM python:3.8

WORKDIR /code
#COPY . /code
COPY requirements.txt /
RUN pip install -r /requirements.txt

EXPOSE 8000
CMD ["python", "main.py"]
