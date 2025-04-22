from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.utils.logging_util import setup_logger
from app.utils.postgresql_db_util import db_util


class DatabaseOperatorUtil:

    def __init__(self):

        self.logger = setup_logger(__name__)

    @staticmethod
    def _filter_valid_fields(model, data):

        model_columns = {column.key for column in inspect(model).columns}
        return {key: value for key, value in data.items() if key in model_columns}

    async def save_to_database(self, model, data: dict, filter_by: dict, update_fields: dict = None, hash_value: str = None, hash_field: str = 'hash'):
        """
        Generic method to save or update an entry in the database.

        :param model: SQLAlchemy model class to operate on
        :param data: Data dictionary to create a new entry if none exists
        :param filter_by: Dictionary of fields to filter by, e.g., {'userId': 'some_id'}
        :param update_fields: Optional dictionary of fields to update if entry exists, e.g., {'status': 'new_status'}
        """
        session: Session = db_util.get_session()

        try:
            with session.begin():

                existing_entry = session.query(model).filter_by(**filter_by).first()

                if existing_entry:
                    if update_fields:
                        for key, value in update_fields.items():
                            setattr(existing_entry, key, value)
                else:
                    filtered_data = self._filter_valid_fields(model, data)
                    if hash_value:
                        filtered_data[hash_field] = hash_value
                    new_entry = model(**filtered_data)
                    session.add(new_entry)

            session.commit()

        except IntegrityError as db_err:
            session.rollback()
            self.logger.error(f'Duplicate entry detected with filters {filter_by}: {db_err}')
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='Duplicate entry detected.')
        except SQLAlchemyError as db_err:
            session.rollback()
            self.logger.error(f'Failed to save to database for model {model.__name__} with filters {filter_by}: {db_err}')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Database save error.')
        finally:
            session.close()
            self.logger.info(f'Session closed after saving to database for model {model.__name__}')

    async def find_all(self, model, filter_expr) -> list:
        """
        Retrieves all entries matching the filter expression.

        :param model: SQLAlchemy model class to query
        :param filter_expr: SQLAlchemy filter expression
        :return: List of model instances matching the query
        """
        session: Session = db_util.get_session()

        try:
            with session.begin():
                results = session.query(model).filter(filter_expr).all()
                self.logger.info(f'Found {len(results)} entries matching filter expression.')
                return [instance.to_dict() for instance in results]

        except SQLAlchemyError as db_err:
            self.logger.error(f'Error finding entries with filter expression: {db_err}')
            return []

        finally:
            session.close()
            self.logger.info('Session closed after find_all operation.')

    async def find_one(self, model, filter_expr):
        """
        Retrieves a single entry matching the filter expression.

        :param model: SQLAlchemy model class to query
        :param filter_expr: SQLAlchemy filter expression
        :return: Single model instance matching the query or None
        """
        session: Session = db_util.get_session()

        try:
            with session.begin():
                result = session.query(model).filter(filter_expr).first()
                if result:
                    self.logger.info('Entry found for filter expression.')
                    return result.to_dict()
                else:
                    self.logger.info('No entry found for filter expression.')
                    return {}

        except SQLAlchemyError as db_err:
            self.logger.error(f'Error finding entry with filter expression: {db_err}')
            return {}

        finally:
            session.close()
            self.logger.info('Session closed after find_one operation.')

    async def update_database(self, model, filter_expr, update_data: dict):
        """
        Updates entries matching the filter expression with the provided data.

        :param model: SQLAlchemy model class to operate on
        :param filter_expr: SQLAlchemy filter expression
        :param update_data: Dictionary of fields to update
        """
        session: Session = db_util.get_session()

        try:
            with session.begin():
                updated_count = session.query(model).filter(filter_expr).update(update_data)
            session.commit()
            self.logger.debug(f'Updated {updated_count} entries matching filter expression with data {update_data}')

        except SQLAlchemyError as db_err:
            session.rollback()
            self.logger.error(f'Error updating entries with filter expression: {db_err}')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Database update error.')
        finally:
            session.close()
            self.logger.info('Session closed after update_database operation.')


database_operator_util = DatabaseOperatorUtil()
