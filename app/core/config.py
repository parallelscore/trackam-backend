import os
from dotenv import load_dotenv
from typing import List, ClassVar
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    PROJECT_NAME: str = Field('Swift Track Backend', json_schema_extra={'env': 'PROJECT_NAME'})
    DESCRIPTION: str = Field('This is the backend service for Swift Track',
                             json_schema_extra={'env': 'DESCRIPTION'})
    VERSION: str = Field('1.0.0', json_schema_extra={'env': 'VERSION'})
    CORS_ORIGINS: List[str] = Field(default=['http://localhost:3000', 'http://localhost:8000'], json_schema_extra={'env': 'CORS_ORIGINS'})
    API_V1_STR: str = Field('/api/v1', json_schema_extra={'env': 'API_V1_STR'})

    POSTGRESQL_DATABASE_URL: str = Field(..., json_schema_extra={'env': 'POSTGRESQL_DATABASE_URL'})

    OTP_EXPIRY_SECONDS: int = Field(600, json_schema_extra={'env': 'OTP_EXPIRY_SECONDS'})
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(10080, json_schema_extra={'env': 'ACCESS_TOKEN_EXPIRE_MINUTES'})

    SMS_SERVICE_ENABLED: bool = Field(True, json_schema_extra={'env': 'SMS_SERVICE_ENABLED'})
    WHATSAPP_SERVICE_ENABLED: bool = Field(True, json_schema_extra={'env': 'WHATSAPP_SERVICE_ENABLED'})
    TWILIO_ACCOUNT_SID: str = Field(..., json_schema_extra={'env': 'TWILIO_ACCOUNT_SID'})
    TWILIO_AUTH_TOKEN: str = Field(..., json_schema_extra={'env': 'TWILIO_AUTH_TOKEN'})
    TWILIO_PHONE_NUMBER: str = Field(..., json_schema_extra={'env': 'TWILIO_PHONE_NUMBER'})
    TWILIO_WHATSAPP_NUMBER: str = Field(..., json_schema_extra={'env': 'TWILIO_WHATSAPP_NUMBER'})

    SECRET_KEY: str = Field(..., json_schema_extra={'env': 'SECRET_KEY'})
    ALGORITHM: str = Field('HS256', json_schema_extra={'env': 'ALGORITHM'})

    FRONTEND_URL: str = Field(..., json_schema_extra={'env': 'FRONTEND_URL'})

    model_config: ClassVar[ConfigDict] = ConfigDict(
        arbitrary_types_allowed=True,
    )


class DevConfig(BaseConfig):
    DEBUG: bool = Field(True, json_schema_extra={'env': 'DEBUG'})


class DemoConfig(BaseConfig):
    DEBUG: bool = Field(True, json_schema_extra={'env': 'DEBUG'})


class ProdConfig(BaseConfig):
    DEBUG: bool = Field(False, json_schema_extra={'env': 'DEBUG'})


def get_settings():
    env = os.getenv('ENV', '').lower()

    env_mapping = {
        'prod': ('.env.prod', ProdConfig),
        'demo': ('.env.demo', DemoConfig),
        'dev': ('.env.dev', DevConfig),
    }

    # If ENV is not specified, default to the basic .env file
    if not env:
        load_dotenv('.env')
        return BaseConfig()

    # Load the environment-specific .env file if ENV is specified
    env_file, config_class = env_mapping.get(env, ('.env', BaseConfig))

    # Load the env file only if it exists
    if os.path.exists(env_file):
        print(f'Loading {env} configuration from {env_file}')
        load_dotenv(env_file)
    else:
        print(f'Environment file {env_file} does not exist')

    return config_class()


settings = get_settings()
