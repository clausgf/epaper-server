FROM python:3.11

WORKDIR /code
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r /requirements.txt

#COPY . /code

EXPOSE 8000
# this is the debug configuration:
CMD ["uvicorn", "backend.main:app", "--proxy-headers", "--no-server-header", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# this is the production configuration:
#CMD ["uvicorn", "backend.main:app", "--proxy-headers", "--no-server-header", "--host", "0.0.0.0", "--port", "8000"]
