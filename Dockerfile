FROM python:3.11

WORKDIR /code
COPY requirements.txt /
RUN pip install --no-cache-dir --upgrade -r /requirements.txt

#COPY . /code

EXPOSE 8000
#CMD ["python", "main.py"]
# debug configuration
CMD ["uvicorn", "backend.main:app", "--proxy-headers", "--no-server-header", "--host", "0.0.0.0", "--port", "8000", "--reload"]
