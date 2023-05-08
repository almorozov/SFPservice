FROM python:3

WORKDIR /app

COPY cfg_env/requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7000

ENTRYPOINT ["./SFP_start.sh"]