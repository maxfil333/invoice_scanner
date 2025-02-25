from pydantic import BaseModel, Field


class SupplierDetails(BaseModel):
    inn: str = Field(..., title="ИНН")
    kpp: str = Field(..., title="КПП")
    bik: str = Field(..., title="БИК")
    cs: str = Field(..., title="Корреспондентский счет")
    rs: str = Field(..., title="Расчетный счет")


class CustomerDetails(BaseModel):
    inn: str = Field(..., title="ИНН")
    kpp: str = Field(..., title="КПП")


class Details(BaseModel):
    supplier: SupplierDetails = Field(..., title="Реквизиты поставщика")
    customer: CustomerDetails = Field(..., title="Реквизиты покупателя")


class ResponseDetails(BaseModel):
    details: Details

