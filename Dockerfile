FROM apache/airflow:3.0.2-python3.11

ENV AIRFLOW_HOME=/opt/airflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./dags ${AIRFLOW_HOME}/dags
COPY ./plugins ${AIRFLOW_HOME}/plugins
COPY ./airflow.cfg ${AIRFLOW_HOME}/airflow.cfg

USER ${AIRFLOW_UID}