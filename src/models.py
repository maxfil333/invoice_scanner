import json

from pydantic import BaseModel, Field
from config.config import NAMES


class SupplierDetails(BaseModel):
    inn: str = Field(..., description="ИНН поставщика")
    kpp: str = Field(..., description="КПП поставщика")
    bik: str = Field(..., description="БИК поставщика")
    cs: str = Field(..., description="Корреспондентский счет поставщика")
    rs: str = Field(..., description="Расчетный счет поставщика")


class CustomerDetails(BaseModel):
    inn: str = Field(..., description="ИНН покупателя")
    kpp: str = Field(..., description="КПП покупателя")


class Details(BaseModel):
    supplier: SupplierDetails
    customer: CustomerDetails


class ResponseDetails(BaseModel):
    details: Details


def processResponseDetails(response: str) -> str:
    response = json.loads(response)
    result = {
        NAMES.supplier:
            {
                "ИНН": response['details']['supplier']['inn'],
                "КПП": response['details']['supplier']['kpp'],
                "БИК": response['details']['supplier']['bik'],
                "корреспондентский счет": response['details']['supplier']['cs'],
                "расчетный счет": response['details']['supplier']['rs']
            },
        NAMES.customer:
            {
                "ИНН": response['details']['customer']['inn'],
                "КПП": response['details']['customer']['kpp']
            }
    }
    return json.dumps(result, ensure_ascii=False)
