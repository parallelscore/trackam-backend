# Use an official Python runtime as a parent image
FROM python:3.12-slim

ARG POSTGRESQL_DATABASE_URL
ARG OTP_EXPIRY_SECONDS
ARG ACCESS_TOKEN_EXPIRE_MINUTES
ARG SMS_SERVICE_ENABLED
ARG WHATSAPP_SERVICE_ENABLED
ARG TWILIO_ACCOUNT_SID
ARG TWILIO_AUTH_TOKEN
ARG TWILIO_PHONE_NUMBER
ARG TWILIO_WHATSAPP_NUMBER
ARG SECRET_KEY
ARG ALGORITHM
ARG FRONTEND_URL

# Set environment variables
ENV POSTGRESQL_DATABASE_URL=$POSTGRESQL_DATABASE_URL
ENV OTP_EXPIRY_SECONDS=$OTP_EXPIRY_SECONDS
ENV ACCESS_TOKEN_EXPIRE_MINUTES=$ACCESS_TOKEN_EXPIRE_MINUTES
ENV SMS_SERVICE_ENABLED=$SMS_SERVICE_ENABLED
ENV WHATSAPP_SERVICE_ENABLED=$WHATSAPP_SERVICE_ENABLED
ENV TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID
ENV TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN
ENV TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER
ENV TWILIO_WHATSAPP_NUMBER=$TWILIO_WHATSAPP_NUMBER
ENV SECRET_KEY=$SECRET_KEY
ENV ALGORITHM=$ALGORITHM
ENV FRONTEND_URL=$FRONTEND_URL

# Set the working directory in the container to /home
WORKDIR /home

# Create apa directory inside /home
RUN mkdir /home/app

# Add the module directory contents into the container at /home/app
ADD ./app /home/app

RUN ls -R /home

# Copy the requirements file into the container at /home
ADD ./requirements.txt /home

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run app.py when the container launches
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
