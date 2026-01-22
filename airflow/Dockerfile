FROM apache/airflow:3.1.6-python3.12

# เปลี่ยนเป็น user root เพื่อติดตั้ง packages ระบบ (ถ้าจำเป็น)
USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean

# กลับมาเป็น user airflow เพื่อลง python packages
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt