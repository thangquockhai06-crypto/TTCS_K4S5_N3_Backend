from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CreatePdfTemplateDTO(BaseModel):
    name: str
    templateType: str = Field("quotation", serialization_alias="templateType")  # quotation | contract
    logoUrl: Optional[str] = Field(None, serialization_alias="logoUrl")
    companyName: str = Field(..., serialization_alias="companyName")
    companyTaxCode: Optional[str] = Field(None, serialization_alias="companyTaxCode")
    companyAddress: Optional[str] = Field(None, serialization_alias="companyAddress")
    companyPhone: Optional[str] = Field(None, serialization_alias="companyPhone")
    companyEmail: Optional[str] = Field(None, serialization_alias="companyEmail")
    companyBankAccount: Optional[str] = Field(None, serialization_alias="companyBankAccount")
    headerText: Optional[str] = Field(None, serialization_alias="headerText")
    footerText: Optional[str] = Field(None, serialization_alias="footerText")
    termsAndConditions: Optional[str] = Field(None, serialization_alias="termsAndConditions")
    isDefault: bool = Field(False, serialization_alias="isDefault")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UpdatePdfTemplateDTO(BaseModel):
    name: Optional[str] = None
    templateType: Optional[str] = Field(None, serialization_alias="templateType")
    logoUrl: Optional[str] = Field(None, serialization_alias="logoUrl")
    companyName: Optional[str] = Field(None, serialization_alias="companyName")
    companyTaxCode: Optional[str] = Field(None, serialization_alias="companyTaxCode")
    companyAddress: Optional[str] = Field(None, serialization_alias="companyAddress")
    companyPhone: Optional[str] = Field(None, serialization_alias="companyPhone")
    companyEmail: Optional[str] = Field(None, serialization_alias="companyEmail")
    companyBankAccount: Optional[str] = Field(None, serialization_alias="companyBankAccount")
    headerText: Optional[str] = Field(None, serialization_alias="headerText")
    footerText: Optional[str] = Field(None, serialization_alias="footerText")
    termsAndConditions: Optional[str] = Field(None, serialization_alias="termsAndConditions")
    isDefault: Optional[bool] = Field(None, serialization_alias="isDefault")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PdfTemplateDTO(BaseModel):
    id: str
    name: str
    templateType: str = Field(..., serialization_alias="templateType")
    logoUrl: Optional[str] = Field(None, serialization_alias="logoUrl")
    companyName: str = Field(..., serialization_alias="companyName")
    companyTaxCode: Optional[str] = Field(None, serialization_alias="companyTaxCode")
    companyAddress: Optional[str] = Field(None, serialization_alias="companyAddress")
    companyPhone: Optional[str] = Field(None, serialization_alias="companyPhone")
    companyEmail: Optional[str] = Field(None, serialization_alias="companyEmail")
    companyBankAccount: Optional[str] = Field(None, serialization_alias="companyBankAccount")
    headerText: Optional[str] = Field(None, serialization_alias="headerText")
    footerText: Optional[str] = Field(None, serialization_alias="footerText")
    termsAndConditions: Optional[str] = Field(None, serialization_alias="termsAndConditions")
    isDefault: bool = Field(False, serialization_alias="isDefault")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
