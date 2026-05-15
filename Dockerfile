FROM python:3.11

# Install node
RUN apt-get update && apt-get install -y nodejs npm

# Install agentcash
RUN npm install -g agentcash

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]