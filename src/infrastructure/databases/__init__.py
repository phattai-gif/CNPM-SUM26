# Import Base trước
from infrastructure.databases.base import Base

# Import tất cả models để SQLAlchemy đăng ký vào Base.metadata
from infrastructure.models import (
    course_register_model,
    todo_model,
    user_model,
    course_model,
    consultant_model,
    appointment_model,
    program_model,
    feedback_model,
    survey_model,
)

from infrastructure.models.auth import (
    auth_user_model,
    auth_role_model,
    auth_funtion_model,
)

from infrastructure.models.sell import (
    sell_customer_model,
    sell_product_model,
    sell_invoice_model,
)

from infrastructure.models.pay import (
    pay_tran_model,
)

# Database factory
from infrastructure.databases.factory_database import FactoryDatabase


def init_db(app):
    database = FactoryDatabase.get_database("POSTGREE")
    database.init_database(app)